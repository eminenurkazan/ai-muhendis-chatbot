"""Seçilen 10 soruluk değerlendirme setini yerel /ask API'sinde çalıştırır.

Örnek: python evaluate_api.py --questions evaluation_questions_v2.json
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = ROOT / "evaluation_questions_v1.json"
OUTPUT_DIR = ROOT / "outputs_local"
ENDPOINT = "http://127.0.0.1:8000/ask"


def ask(question: str) -> dict:
    token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
    if not token:
        raise ValueError("Önce giriş yapıp APP_ACCESS_TOKEN ortam değişkenini tanımla.")
    # Beklenen kaynaklar modele gönderilmez; yalnız soru gönderilir.
    body = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
    request = Request(
        ENDPOINT, data=body,
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {token}"}, method="POST",
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_questions(path: Path) -> list[dict]:
    questions = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(questions, list) or len(questions) != 10:
        raise ValueError("Değerlendirme dosyasında tam 10 soru olmalı.")
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
            raise ValueError(f"{question_id}: beklenen ticketlar benzersiz kimlik listesi olmalı.")
        if type(no_source) is not bool or no_source != (not expected):
            raise ValueError(f"{question_id}: beklenen kaynak ile kaynak-yok bayrağı tutarsız.")
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
    valid_used = set(used).issubset(retrieved) and all(tid in answer["answer"] for tid in used)
    return {
        "question_id": item["question_id"], "question": item["question"],
        "expected_ticket_ids": expected, "retrieved_ticket_ids": retrieved,
        "top3_hit": None if no_source else bool(set(expected) & set(retrieved[:3])),
        "expected_source_rank": min(ranks) if ranks else None,
        "used_ticket_ids": used, "used_sources_valid": valid_used,
        "expected_insufficient_context": no_source,
        "insufficient_context": answer["insufficient_context"],
        "no_source_pass": (answer["insufficient_context"] is True and not used) if no_source else None,
        "expected_source_used": None if no_source else bool(set(expected) & set(used)),
        "elapsed_ms": answer["elapsed_ms"], "answer": answer["answer"],
        "expertise_mode": answer.get("expertise_mode"),
        "prompt_version": answer.get("prompt_version"),
        "grounding_review": "manual_review_needed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH,
                        help="10 soruluk JSON dosyası; varsayılan V1.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Her soru sonrası sonuçların kaydedileceği klasör.")
    args = parser.parse_args()
    question_path = args.questions.resolve()
    questions = load_questions(question_path)
    if not os.environ.get("APP_ACCESS_TOKEN", "").strip():
        parser.error("Önce giriş yapıp APP_ACCESS_TOKEN ortam değişkenini tanımla.")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    label = re.sub(r"[^A-Za-z0-9_-]", "_", question_path.stem.removeprefix("evaluation_questions_"))
    run_name = f"evaluation_results_{label}_{now:%Y%m%d_%H%M%S_%f}"
    output_path = output_dir / f"{run_name}.json"
    meta_path = output_dir / f"{run_name}.meta.json"
    rows: list[dict] = []
    metadata = {
        "status": "running", "started_at": now.isoformat(),
        "questions_path": str(question_path),
        "questions_sha256": hashlib.sha256(question_path.read_bytes()).hexdigest(),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "endpoint": ENDPOINT, "planned_count": len(questions),
        "results_path": str(output_path), "completed_count": 0,
        "requested_expertise_mode": "service_desk (API default)",
    }
    save(meta_path, metadata)
    save(output_path, rows)
    print(f"Soru dosyası: {question_path}", flush=True)
    print(f"{len(questions)} soru sırayla çalıştırılıyor; bulut istekleri biraz sürebilir.\n", flush=True)
    failed = False
    for item in questions:
        question_id = item["question_id"]
        try:
            row = result_row(item, ask(item["question"]))
        except HTTPError as exc:
            rows.append({"question_id": question_id, "question": item["question"],
                         "error": f"HTTP {exc.code}",
                         "detail": exc.read(2000).decode("utf-8", errors="replace")})
            print(f"{question_id}: API hatası HTTP {exc.code}; test durduruldu.", flush=True)
            failed = True
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            rows.append({"question_id": question_id, "question": item["question"],
                         "error": type(exc).__name__})
            print(f"{question_id}: bağlantı veya yanıt biçimi hatası; test durduruldu.", flush=True)
            failed = True
        if failed:
            save(output_path, rows)
            break
        rows.append(row)
        save(output_path, rows)
        metadata["completed_count"] = len(rows)
        save(meta_path, metadata)
        verdict = (
            f"kaynak yok testi={'GEÇTİ' if row['no_source_pass'] else 'KALDI'}"
            if item["expected_insufficient_context"] else
            f"ilk 3={'GEÇTİ' if row['top3_hit'] else 'KALDI'}"
        )
        print(f"{question_id}: {verdict}; bulunan={','.join(row['retrieved_ticket_ids'])}; süre={row['elapsed_ms']} ms", flush=True)
    completed = [row for row in rows if "error" not in row]
    relevant = [row for row in completed if row["top3_hit"] is not None]
    no_source = [row for row in completed if row["no_source_pass"] is not None]
    metadata.update(
        status="failed" if failed else "completed",
        finished_at=datetime.now().astimezone().isoformat(), completed_count=len(completed),
        top3_hits=sum(row["top3_hit"] for row in relevant), relevant_count=len(relevant),
        no_source_passes=sum(row["no_source_pass"] for row in no_source),
        no_source_count=len(no_source), grounding_review="manual_review_needed",
    )
    if completed:
        metadata["mean_elapsed_ms"] = round(sum(row["elapsed_ms"] for row in completed) / len(completed))
    save(meta_path, metadata)
    print(f"\nSonuç dosyası: {output_path}", flush=True)
    print(f"Tamamlanan soru: {len(completed)}/{len(questions)}", flush=True)
    print(f"İlk 3 içinde beklenen kaynak: {metadata['top3_hits']}/{len(relevant)}", flush=True)
    print(f"Kaynakta karşılığı olmayan soru: {metadata['no_source_passes']}/{len(no_source)}", flush=True)
    if completed:
        print(f"Ortalama süre: {metadata['mean_elapsed_ms']} ms", flush=True)
    print("Yanıtların kaynağa bağlılığı ayrıca incelenecek.", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
