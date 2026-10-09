"""Önceden hazırlanmış 10 soruyu yerel /ask API'sinde değerlendirir."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = ROOT / "evaluation_questions_v1.json"
OUTPUT_DIR = ROOT / "outputs_local"
ENDPOINT = "http://127.0.0.1:8000/ask"


def ask(question: str) -> dict:
    body = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
    request = Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def save(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(questions, list) or len(questions) != 10:
        raise ValueError("Değerlendirme dosyasında tam 10 soru olmalı.")
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"evaluation_results_v1_{datetime.now():%Y%m%d_%H%M%S}.json"
    rows: list[dict] = []

    print("10 soru sırayla çalıştırılıyor. Her soru bulut isteği yaptığı için biraz sürebilir.\n")
    for item in questions:
        question_id = item["question_id"]
        try:
            answer = ask(item["question"])
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            rows.append({"question_id": question_id, "error": f"HTTP {exc.code}: {detail}"})
            save(output_path, rows)
            print(f"{question_id}: API hatası HTTP {exc.code}; test durduruldu.")
            break
        except (URLError, TimeoutError) as exc:
            rows.append({"question_id": question_id, "error": type(exc).__name__})
            save(output_path, rows)
            print(f"{question_id}: bağlantı hatası; test durduruldu.")
            break

        expected = item["expected_ticket_ids"]
        retrieved = answer["retrieved_ticket_ids"]
        used = answer["used_ticket_ids"]
        no_source_expected = item["expected_insufficient_context"]
        row = {
            "question_id": question_id,
            "question": item["question"],
            "expected_ticket_ids": expected,
            "retrieved_ticket_ids": retrieved,
            "top3_hit": None if no_source_expected else bool(set(expected) & set(retrieved)),
            "used_ticket_ids": used,
            "used_sources_valid": set(used).issubset(retrieved) and all(ticket_id in answer["answer"] for ticket_id in used),
            "expected_insufficient_context": no_source_expected,
            "insufficient_context": answer["insufficient_context"],
            "no_source_pass": (
                answer["insufficient_context"] is True and not used
                if no_source_expected else None
            ),
            "elapsed_ms": answer["elapsed_ms"],
            "answer": answer["answer"],
            "grounding_review": "manual_review_needed",
        }
        rows.append(row)
        save(output_path, rows)
        verdict = (
            f"kaynak yok testi={'GEÇTİ' if row['no_source_pass'] else 'KALDI'}"
            if no_source_expected else f"ilk 3={'GEÇTİ' if row['top3_hit'] else 'KALDI'}"
        )
        print(f"{question_id}: {verdict}; bulunan={','.join(retrieved)}; süre={answer['elapsed_ms']} ms")

    completed = [row for row in rows if "error" not in row]
    relevant = [row for row in completed if row["top3_hit"] is not None]
    no_source = [row for row in completed if row["no_source_pass"] is not None]
    print(f"\nSonuç dosyası: {output_path}")
    print(f"İlk 3 içinde beklenen kaynak: {sum(row['top3_hit'] for row in relevant)}/{len(relevant)}")
    print(f"Kaynakta karşılığı olmayan soru: {sum(row['no_source_pass'] for row in no_source)}/{len(no_source)}")
    if completed:
        mean_ms = round(sum(row["elapsed_ms"] for row in completed) / len(completed))
        print(f"Ortalama süre: {mean_ms} ms")
    print("Yanıtların kaynağa bağlılığı henüz elle incelenmedi.")


if __name__ == "__main__":
    main()
