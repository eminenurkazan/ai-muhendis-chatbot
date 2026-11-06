"""Windows/Oracle için kaynaklı QA adayları indirir; embedding veya DB yazımı yapmaz."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API = "https://api.stackexchange.com/2.3"
LICENSES = {
    f"CC BY-SA {version}": f"https://creativecommons.org/licenses/by-sa/{version}/"
    for version in ("2.5", "3.0", "4.0")
}
# Etiketleri tek tek sorgula; konu/sürüm bazında kapsam raporlanabilsin.
TOPICS = {
    "serverfault": [
        ("active_directory", {"tagged": "active-directory"}),
        ("iis", {"tagged": "iis"}),
        ("event_log", {"tagged": "windows-event-log"}),
        ("event_log", {"tagged": "eventviewer"}),
        ("windows_server", {"tagged": "windows-server-2016"}),
        ("windows_server", {"tagged": "windows-server-2019"}),
        ("windows_server", {"tagged": "windows-server-2022"}),
        ("windows_server", {"tagged": "windows-server-2025"}),
    ],
    "dba": [
        ("sql_performance", {"tagged": "oracle", "title": "performance"}),
        ("sql_performance", {"tagged": "oracle", "title": "slow"}),
        ("tablespace", {"tagged": "oracle", "title": "tablespace"}),
        ("backup_recovery", {"tagged": "oracle", "title": "backup"}),
        ("backup_recovery", {"tagged": "oracle", "title": "rman"}),
        ("oracle_general", {"tagged": "oracle"}),
    ],
}


class MarkdownText(HTMLParser):
    """Paragraf ve kod sınırlarını korur; kaynak HTML ayrıca saklanır."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.pre = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "pre":
            self.pre = True
            self.parts.append("\n```\n")
        elif tag == "code" and not self.pre:
            self.parts.append("`")
        elif tag in {"p", "div", "blockquote", "h1", "h2", "h3", "br"}:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "a":
            href = attributes.get("href", "")
            self.links.append(href if urlsplit(href).scheme in {"https", "http"} else "")
            self.parts.append("[")
        elif tag == "img":
            self.parts.append("[image: " + attributes.get("alt", "") + "]")

    def handle_endtag(self, tag):
        if tag == "pre":
            self.pre = False
            self.parts.append("\n```\n")
        elif tag == "code" and not self.pre:
            self.parts.append("`")
        elif tag in {"p", "div", "blockquote", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")
        elif tag == "a" and self.links:
            href = self.links.pop()
            self.parts.append("](" + href + ")" if href else "]")

    def handle_data(self, data):
        self.parts.append(data)


def text_from_html(value: str) -> str:
    parser = MarkdownText()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts).strip()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PublicAPI:
    def __init__(self, output: Path):
        self.output = output
        self.cache = ROOT / "outputs_local" / "stackexchange_api_cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.requests = []

    def get(self, endpoint: str, **parameters) -> dict:
        url = API + endpoint + "?" + urlencode(parameters)
        cache_path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        cached = cache_path.exists() and time.time() - cache_path.stat().st_mtime < 86400
        if cached:
            envelope = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            request = Request(url, headers={"User-Agent": "ai-muhendis-chatbot-dataset/0.1"})
            with urlopen(request, timeout=30) as response:
                raw = response.read()
            if raw.startswith(b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            data = json.loads(raw)
            if "error_id" in data:
                raise RuntimeError(f"Stack Exchange API error: {data['error_id']}")
            envelope = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(), "response": data}
            write_json(cache_path, envelope)
        data = envelope["response"]
        self.requests.append({"url": url, "cached": cached, "fetched_at": envelope["fetched_at"],
                              "quota_remaining": data.get("quota_remaining")})
        write_json(self.output / "raw" / f"request_{len(self.requests):03}.json", envelope)
        if not cached:
            backoff = data.get("backoff", 0)
            if backoff > 30:
                raise RuntimeError(f"API {backoff} saniye bekleme istedi; ham yanıt kaydedildi. Bu süre dolmadan yeniden çalıştırmayın.")
            time.sleep(max(1, backoff))
        return data


def owner(post: dict) -> dict:
    value = post.get("owner", {})
    return {"name": html.unescape(value.get("display_name", "")), "url": value.get("link", "")}


def make_record(site: str, question: dict, answer: dict | None, topics: list[str]) -> tuple[dict | None, str]:
    if answer is None:
        return None, "accepted_answer_missing"
    if answer.get("answer_id") != question.get("accepted_answer_id") or answer.get("question_id") != question["question_id"] or answer.get("is_accepted") is not True:
        return None, "answer_pair_mismatch"
    if answer.get("score", 0) < 1:
        return None, "answer_score_below_1"
    if any(post.get("content_license") not in LICENSES for post in (question, answer)):
        return None, "license_missing_or_unknown"
    if any(not owner(post)["name"] or not owner(post)["url"] for post in (question, answer)):
        return None, "attribution_incomplete"
    question_text = text_from_html(question.get("body", ""))
    answer_text = text_from_html(answer.get("body", ""))
    if len(question_text) < 80 or len(answer_text) < 120:
        return None, "text_too_short"
    tags = question.get("tags", [])
    if site == "dba" and "oracle" not in tags:
        return None, "not_oracle"
    if site == "serverfault" and ("samba" in tags or "linux" in tags) and not any(tag.startswith("windows-server") for tag in tags):
        return None, "mixed_platform_without_windows_server_tag"
    host = "serverfault.com" if site == "serverfault" else "dba.stackexchange.com"
    flags = []
    if "<img" in question.get("body", "") + answer.get("body", ""):
        flags.append("contains_image_check_missing_context")
    if any(any(version in tag for version in ("2003", "2008", "2012", "9i", "10g", "11g")) for tag in tags):
        flags.append("older_product_version_check_applicability")
    record = {
        "source_record_id": f"{site}:q{question['question_id']}:a{answer['answer_id']}",
        "source_name": "Server Fault" if site == "serverfault" else "Database Administrators",
        "record_type": "qa", "domain": "windows_server" if site == "serverfault" else "oracle_db",
        "title": html.unescape(question["title"]), "problem": question_text, "solution": answer_text,
        "source_url": question["link"], "answer_url": f"https://{host}/a/{answer['answer_id']}",
        "question_author": owner(question), "answer_author": owner(answer),
        "question_license": question["content_license"], "answer_license": answer["content_license"],
        "question_license_url": LICENSES[question["content_license"]], "answer_license_url": LICENSES[answer["content_license"]],
        "question_id": question["question_id"], "answer_id": answer["answer_id"],
        "tags": tags, "topics": sorted(set(topics)),
        "question_score": question.get("score", 0), "answer_score": answer["score"],
        "answer_accepted": True, "resolution_confirmed": None,
        "question_created_at": question.get("creation_date"), "question_edited_at": question.get("last_edit_date"),
        "answer_created_at": answer.get("creation_date"), "answer_edited_at": answer.get("last_edit_date"),
        "review_status": "pending", "index_status": "pending", "review_flags": flags,
        "limitations": "Community Q&A; accepted answer is not an independently reproduced fix. Product version, commands, risks and applicability need review.",
        "transformation": "HTML converted to Markdown-like text; original API responses preserved. No LLM answer generation or summarization.",
        "source_content_hash": hashlib.sha256((question.get("body", "") + "\n" + answer.get("body", "")).encode()).hexdigest(),
    }
    return record, "eligible_pending_review"


def collect(per_topic: int, per_domain: int) -> Path:
    output = ROOT / "outputs_local" / "expertise_qa" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    (output / "raw").mkdir(parents=True, exist_ok=False)
    api = PublicAPI(output)
    records = []
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "domains": {},
              "scope": "Accepted community Q&A candidates; no embeddings or PostgreSQL changes.",
              "from_question_creation_year": 2018, "per_query_limit": per_topic, "per_domain_limit": per_domain}
    try:
        for site, queries in TOPICS.items():
            questions = {}
            topic_map = {}
            query_counts = []
            for topic, query in queries:
                data = api.get("/search/advanced", site=site, accepted="true", closed="false", migrated="false",
                               sort="votes", order="desc", min=0, fromdate=1514764800,
                               pagesize=per_topic, page=1, filter="withbody", **query)
                items = data.get("items", [])
                query_counts.append({"topic": topic, "query": query, "count": len(items), "has_more": data.get("has_more")})
                for item in items:
                    questions[item["question_id"]] = item
                    topic_map.setdefault(item["question_id"], []).append(topic)
                print(f"{site}/{topic}: {len(items)} questions", flush=True)
            accepted_ids = sorted({q["accepted_answer_id"] for q in questions.values() if "accepted_answer_id" in q})
            answers = {}
            for offset in range(0, len(accepted_ids), 100):
                ids = ";".join(map(str, accepted_ids[offset:offset + 100]))
                data = api.get("/answers/" + ids, site=site, pagesize=100, filter="withbody")
                answers.update({a["answer_id"]: a for a in data.get("items", [])})
            eligible, excluded = [], Counter()
            for question_id, question in questions.items():
                record, reason = make_record(site, question, answers.get(question.get("accepted_answer_id")), topic_map[question_id])
                if record is None:
                    excluded[reason] += 1
                else:
                    eligible.append(record)
            # Konuları dönüşümlü seçerek tek bir popüler konunun tüm seti doldurmasını önle.
            selected, used = [], set()
            buckets = {topic: [r for r in eligible if topic in r["topics"]] for topic, _ in queries}
            while len(selected) < per_domain and any(buckets.values()):
                for bucket in buckets.values():
                    while bucket and bucket[0]["source_record_id"] in used:
                        bucket.pop(0)
                    if bucket and len(selected) < per_domain:
                        record = bucket.pop(0)
                        selected.append(record)
                        used.add(record["source_record_id"])
            records.extend(selected)
            report["domains"][site] = {"queries": query_counts, "unique_questions": len(questions),
                "eligible_count": len(eligible), "selected_count": len(selected), "excluded": dict(excluded),
                "topic_counts": dict(Counter(topic for r in selected for topic in r["topics"])),
                "review_flag_counts": dict(Counter(flag for r in selected for flag in r["review_flags"]))}
            print(f"{site}: {len(selected)} candidates, all pending review", flush=True)
        with (output / "candidates.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        attribution = ["# Source attribution", "", "HTML formatting was converted; original API responses are in raw/. All records require review.", ""]
        for record in records:
            attribution.extend([f"## {record['source_record_id']}", record["title"],
                f"Question: {record['question_author']['name']} ({record['question_author']['url']}) — {record['source_url']} — {record['question_license']} ({record['question_license_url']})",
                f"Answer: {record['answer_author']['name']} ({record['answer_author']['url']}) — {record['answer_url']} — {record['answer_license']} ({record['answer_license_url']})", ""])
        (output / "ATTRIBUTION.md").write_text("\n".join(attribution), encoding="utf-8")
        report["status"] = "collected_pending_review"
        report["total_candidates"] = len(records)
        report["api_requests"] = api.requests
        write_json(output / "manifest.json", report)
    except Exception as exc:
        report.update(status="incomplete", error_type=type(exc).__name__, api_requests=api.requests)
        write_json(output / "manifest.json", report)
        raise
    print(f"Output: {output}", flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-topic", type=int, default=60)
    parser.add_argument("--per-domain", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.per_topic <= 100 or not 1 <= args.per_domain <= 500:
        parser.error("per-topic 1..100; per-domain 1..500 olmalı.")
    collect(args.per_topic, args.per_domain)


if __name__ == "__main__":
    main()
