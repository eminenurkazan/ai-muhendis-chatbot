"""Değerlendirme soru setini yerel API'de çalıştırır ve sonuçları kaydeder.

Örnekler:
    python evaluate_api.py --questions evaluation_questions_v3.json
    python evaluate_api.py --questions evaluation_questions_v2.json --flow direct

Varsayılan akış (``chat``) arayüzle aynı yolu kullanır: her soru için ayrı bir sohbet
açılır (soruda belirtilen uzmanlık moduyla) ve soru ``/chats/{id}/ask`` ile sorulur;
soru–yanıt MSSQL'e kaydedilir. ``direct`` akışı kayıt yapmayan ``/ask`` ucunu kullanır.
Beklenen kaynaklar ve değerlendirme ölçütleri API'ye gönderilmez.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = ROOT / "evaluation_questions_v1.json"
OUTPUT_DIR = ROOT / "outputs_local"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
EXPERTISE_MODES = ("service_desk", "windows_server", "oracle_db")
MAX_QUESTIONS = 50
REQUEST_TIMEOUT = 180


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.detail = detail


def _post(url: str, body: dict, token: str) -> dict:
    request = Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ApiError(exc.code, exc.read(2000).decode("utf-8", errors="replace")) from None


def ask_direct(base_url: str, token: str, item: dict) -> dict:
    return _post(f"{base_url}/ask", {"question": item["question"], "expertise_mode": item["expertise_mode"]}, token)


def ask_chat(base_url: str, token: str, item: dict) -> dict:
    chat = _post(f"{base_url}/chats", {"title": f"Test {item['question_id']}", "expertise_mode": item["expertise_mode"]}, token)
    return _post(f"{base_url}/chats/{chat['id']}/ask",
                 {"question": item["question"], "request_id": str(uuid.uuid4())}, token)


FLOWS = {"chat": ask_chat, "direct": ask_direct}


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_questions(path: Path) -> list[dict]:
    questions = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(questions, list) or not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError(f"Değerlendirme dosyası 1–{MAX_QUESTIONS} sorudan oluşan bir liste olmalı.")
    seen: set[str] = set()
    for item in questions:
        if not isinstance(item, dict):
            raise ValueError("Her soru bir JSON nesnesi olmalı.")
        question_id = item.get("question_id")
        question = item.get("question")
        expected = item.get("expected_ticket_ids")
        no_source = item.get("expected_insufficient_context")
        if not isinstance(question_id, str) or not question_id.strip() or question_id in seen:
            raise ValueError("Soru kimlikleri dolu ve benzersiz olmalı.")
        seen.add(question_id)
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError(f"{question_id}: soru 1–2000 karakter olmalı.")
        if (not isinstance(expected, list)
                or any(not isinstance(ticket_id, str) or not ticket_id for ticket_id in expected)
                or len(expected) != len(set(expected))):
            raise ValueError(f"{question_id}: beklenen kaynaklar benzersiz kimlik listesi olmalı.")
        if type(no_source) is not bool or no_source != (not expected):
            raise ValueError(f"{question_id}: beklenen kaynak ile kaynak-yok bayrağı tutarsız.")
        item.setdefault("expertise_mode", "service_desk")
        if item["expertise_mode"] not in EXPERTISE_MODES:
            raise ValueError(f"{question_id}: geçersiz uzmanlık modu.")
        item.setdefault("category", "uncategorized")
        if not isinstance(item["category"], str) or not item["category"].strip():
            raise ValueError(f"{question_id}: kategori boş olamaz.")
    return questions


def result_row(item: dict, answer: dict) -> dict:
    if not isinstance(answer, dict) or not isinstance(answer.get("answer"), str):
        raise ValueError("API yanıt metni eksik.")
    for name in ("retrieved_ticket_ids", "used_ticket_ids"):
        if not isinstance(answer.get(name), list) or any(not isinstance(x, str) for x in answer[name]):
            raise ValueError("API kaynak kimliği listesi geçersiz.")
    if type(answer.get("insufficient_context")) is not bool:
        raise ValueError("API kaynak-yetersiz alanı geçersiz.")
    if type(answer.get("elapsed_ms")) is not int or answer["elapsed_ms"] < 0:
        raise ValueError("API süre alanı geçersiz.")
    expected = item["expected_ticket_ids"]
    retrieved = answer["retrieved_ticket_ids"]
    used = answer["used_ticket_ids"]
    no_source = item["expected_insufficient_context"]
    ranks = [n for n, tid in enumerate(retrieved, start=1) if tid in expected]
    return {
        "question_id": item["question_id"], "category": item["category"],
        "requested_expertise_mode": item["expertise_mode"], "question": item["question"],
        "expected_ticket_ids": expected, "retrieved_ticket_ids": retrieved,
        "top3_hit": None if no_source else bool(set(expected) & set(retrieved[:3])),
        "expected_source_rank": min(ranks) if ranks else None,
        "used_ticket_ids": used,
        # Kullanılan kaynaklar arama adaylarının alt kümesi olmalı (uydurma kimlik yok).
        "used_sources_valid": set(used).issubset(retrieved),
        # Bilgi amaçlı: yanıt metni kimlikleri yazmak zorunda değildir.
        "used_ids_cited_in_text": all(tid in answer["answer"] for tid in used),
        "expected_insufficient_context": no_source,
        "insufficient_context": answer["insufficient_context"],
        "no_source_pass": (answer["insufficient_context"] is True and not used) if no_source else None,
        "expected_source_used": None if no_source else bool(set(expected) & set(used)),
        "elapsed_ms": answer["elapsed_ms"], "answer": answer["answer"],
        "expertise_mode": answer.get("expertise_mode"),
        "prompt_version": answer.get("prompt_version"),
        "sources": answer.get("sources"),
        "required_points": item.get("required_points", []),
        "must_not_claim": item.get("must_not_claim", []),
        "grounding_review": "manual_review_needed",
    }


def summarize(rows: list[dict]) -> dict:
    """Tamamlanan satırlardan genel ve kategori bazlı ölçümler."""
    def block(selected: list[dict]) -> dict:
        done = [r for r in selected if "error" not in r]
        relevant = [r for r in done if r["top3_hit"] is not None]
        negative = [r for r in done if r["no_source_pass"] is not None]
        summary = {
            "planned": len(selected), "completed": len(done), "errors": len(selected) - len(done),
            "relevant_count": len(relevant),
            "top3_hits": sum(r["top3_hit"] for r in relevant),
            "rank1_hits": sum(r["expected_source_rank"] == 1 for r in relevant),
            "expected_source_used": sum(bool(r["expected_source_used"]) for r in relevant),
            "no_source_count": len(negative),
            "no_source_passes": sum(r["no_source_pass"] for r in negative),
            "used_sources_valid": sum(r["used_sources_valid"] for r in done),
        }
        if done:
            times = sorted(r["elapsed_ms"] for r in done)
            summary.update(mean_elapsed_ms=round(sum(times) / len(times)),
                           min_elapsed_ms=times[0], max_elapsed_ms=times[-1])
        return summary
    categories = sorted({r["category"] for r in rows})
    return {"overall": block(rows), "by_category": {c: block([r for r in rows if r["category"] == c]) for c in categories}}


def run(questions: list[dict], ask, *, output_path: Path, meta_path: Path, metadata: dict,
        stop_on_error: bool = False, pause_seconds: float = 0.0) -> list[dict]:
    rows: list[dict] = []
    save(meta_path, metadata)
    save(output_path, rows)
    for index, item in enumerate(questions):
        question_id = item["question_id"]
        base = {"question_id": question_id, "category": item["category"],
                "requested_expertise_mode": item["expertise_mode"], "question": item["question"]}
        try:
            row = result_row(item, ask(item))
        except ApiError as exc:
            row = {**base, "error": f"HTTP {exc.status}", "detail": exc.detail}
        except (URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            row = {**base, "error": type(exc).__name__}
        rows.append(row)
        save(output_path, rows)
        metadata["completed_count"] = sum("error" not in r for r in rows)
        save(meta_path, metadata)
        if "error" in row:
            print(f"{question_id}: HATA ({row['error']})", flush=True)
            if stop_on_error:
                break
        else:
            verdict = (f"kaynak yok testi={'GEÇTİ' if row['no_source_pass'] else 'KALDI'}"
                       if item["expected_insufficient_context"] else
                       f"ilk 3={'GEÇTİ' if row['top3_hit'] else 'KALDI'} (sıra={row['expected_source_rank']})")
            print(f"{question_id} [{item['expertise_mode']}]: {verdict}; süre={row['elapsed_ms']} ms", flush=True)
        if pause_seconds and index < len(questions) - 1:
            time.sleep(pause_seconds)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH, help="Soru dosyası; varsayılan V1.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Sonuç klasörü.")
    parser.add_argument("--flow", choices=sorted(FLOWS), default="chat",
                        help="chat: kalıcı sohbet akışı (varsayılan); direct: kayıt yapmayan /ask.")
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE_URL),
                        help="API adresi; varsayılan API_BASE_URL veya http://127.0.0.1:8000.")
    parser.add_argument("--stop-on-error", action="store_true", help="İlk hatada dur (varsayılan: devam et).")
    parser.add_argument("--pause", type=float, default=0.0, help="Sorular arasında beklenecek saniye.")
    args = parser.parse_args()
    question_path = args.questions.resolve()
    questions = load_questions(question_path)
    token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
    if not token:
        parser.error("Önce giriş yapıp APP_ACCESS_TOKEN ortam değişkenini tanımla.")
    base_url = args.base_url.rstrip("/")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    label = re.sub(r"[^A-Za-z0-9_-]", "_", question_path.stem.removeprefix("evaluation_questions_"))
    run_name = f"evaluation_results_{label}_{now:%Y%m%d_%H%M%S_%f}"
    output_path = output_dir / f"{run_name}.json"
    meta_path = output_dir / f"{run_name}.meta.json"
    metadata = {
        "status": "running", "started_at": now.isoformat(),
        "questions_path": str(question_path),
        "questions_sha256": hashlib.sha256(question_path.read_bytes()).hexdigest(),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "base_url": base_url, "flow": args.flow, "planned_count": len(questions),
        "mode_counts": dict(Counter(q["expertise_mode"] for q in questions)),
        "results_path": str(output_path), "completed_count": 0,
    }
    print(f"Soru dosyası: {question_path} ({len(questions)} soru, akış={args.flow})", flush=True)
    print("Bulut istekleri sırayla gönderiliyor; her soru birkaç saniye sürebilir.\n", flush=True)
    ask = FLOWS[args.flow]
    rows = run(questions, lambda item: ask(base_url, token, item), output_path=output_path,
               meta_path=meta_path, metadata=metadata, stop_on_error=args.stop_on_error,
               pause_seconds=args.pause)
    summary = summarize(rows)
    failed = summary["overall"]["errors"] > 0 or len(rows) < len(questions)
    metadata.update(status="completed_with_errors" if failed else "completed",
                    finished_at=datetime.now().astimezone().isoformat(),
                    completed_count=summary["overall"]["completed"], summary=summary,
                    grounding_review="manual_review_needed")
    save(meta_path, metadata)
    overall = summary["overall"]
    print(f"\nSonuç dosyası: {output_path}", flush=True)
    print(f"Tamamlanan soru: {overall['completed']}/{len(questions)}", flush=True)
    for category, block in summary["by_category"].items():
        parts = [f"{block['completed']}/{block['planned']} tamamlandı"]
        if block["relevant_count"]:
            parts.append(f"ilk 3: {block['top3_hits']}/{block['relevant_count']}")
        if block["no_source_count"]:
            parts.append(f"kaynak yok: {block['no_source_passes']}/{block['no_source_count']}")
        if "mean_elapsed_ms" in block:
            parts.append(f"ort. {block['mean_elapsed_ms']} ms")
        print(f"  {category}: " + "; ".join(parts), flush=True)
    print("Yanıtların kaynağa bağlılığı ayrıca elle incelenecek.", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
