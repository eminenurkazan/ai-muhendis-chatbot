"""Çok turlu sohbet senaryolarını yerel API'de çalıştırır ("önceki mesajları hatırlama" isteri).

Örnek:
    python evaluate_conversations.py --conversations evaluation/evaluation_conversations_v1.json

Her senaryo için senaryonun uzmanlık moduyla tek bir sohbet açılır ve sorular aynı sohbette
sırayla ``/chats/{id}/ask`` ile sorulur. Geçmişi istemci göndermez; API, JWT sahibinin MSSQL'deki
sohbetinden okur. Beklenen kaynaklar ve ölçütler API'ye gönderilmez. Bir turda hata olursa o
senaryonun kalan turları atlanır (sonraki turlar geçmişe bağlıdır), diğer senaryolar sürer.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.error import URLError
import uuid

from evaluate_api import DEFAULT_BASE_URL, EXPERTISE_MODES, ApiError, _post, save

ROOT = Path(__file__).resolve().parent
CONVERSATIONS_PATH = ROOT / "evaluation" / "evaluation_conversations_v1.json"
OUTPUT_DIR = ROOT / "outputs_local"
MAX_TURNS = 3


def load_conversations(path: Path) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list) or not items:
        raise ValueError("Senaryo dosyası boş olmayan bir liste olmalı.")
    seen: set[str] = set()
    for item in items:
        cid = item.get("conversation_id") if isinstance(item, dict) else None
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise ValueError("Senaryo kimlikleri dolu ve benzersiz olmalı.")
        seen.add(cid)
        if item.get("expertise_mode") not in EXPERTISE_MODES:
            raise ValueError(f"{cid}: geçersiz uzmanlık modu.")
        turns = item.get("turns")
        if not isinstance(turns, list) or not 2 <= len(turns) <= MAX_TURNS:
            raise ValueError(f"{cid}: senaryo 2–{MAX_TURNS} tur içermeli (API son 3 çifti bağlam olarak kullanır).")
        for number, turn in enumerate(turns, start=1):
            question = turn.get("question") if isinstance(turn, dict) else None
            if not isinstance(question, str) or not question.strip() or len(question) > 2000:
                raise ValueError(f"{cid} tur {number}: soru 1–2000 karakter olmalı.")
            expected = turn.get("expected_ticket_ids")
            if not isinstance(expected, list) or any(not isinstance(x, str) or not x for x in expected):
                raise ValueError(f"{cid} tur {number}: beklenen kaynaklar kimlik listesi olmalı.")
            flag = turn.get("expected_insufficient_context")
            if flag is not None and (type(flag) is not bool or flag != (not expected)):
                raise ValueError(f"{cid} tur {number}: beklenen kaynak ile kaynak-yok bayrağı tutarsız.")
    return items


def turn_row(conversation: dict, number: int, turn: dict, answer: dict) -> dict:
    if not isinstance(answer, dict) or not isinstance(answer.get("answer"), str):
        raise ValueError("API yanıt metni eksik.")
    retrieved = answer.get("retrieved_ticket_ids") or []
    used = answer.get("used_ticket_ids") or []
    expected = turn["expected_ticket_ids"]
    flag = turn.get("expected_insufficient_context")
    return {
        "conversation_id": conversation["conversation_id"], "turn": number,
        "question": turn["question"], "expected_ticket_ids": expected,
        "retrieved_ticket_ids": retrieved, "used_ticket_ids": used,
        "used_sources_valid": set(used).issubset(retrieved),
        "expected_source_used": bool(set(expected) & set(used)) if expected else None,
        "expected_insufficient_context": flag,
        "insufficient_context": answer.get("insufficient_context"),
        "no_source_pass": (answer.get("insufficient_context") is True and not used) if flag is True else None,
        "elapsed_ms": answer.get("elapsed_ms"), "answer": answer["answer"],
        "expertise_mode": answer.get("expertise_mode"), "prompt_version": answer.get("prompt_version"),
        "required_points": turn.get("required_points", []), "must_not_claim": turn.get("must_not_claim", []),
        "grounding_review": "manual_review_needed",
    }


def run(conversations: list[dict], post, base_url: str, token: str, *, output_path: Path) -> list[dict]:
    rows: list[dict] = []
    save(output_path, rows)
    for conversation in conversations:
        cid = conversation["conversation_id"]
        try:
            chat = post(f"{base_url}/chats", {"title": f"Test {cid}", "expertise_mode": conversation["expertise_mode"]}, token)
        except (ApiError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            rows.append({"conversation_id": cid, "turn": 0, "error": getattr(exc, "status", type(exc).__name__)})
            save(output_path, rows)
            print(f"{cid}: sohbet açılamadı; senaryo atlandı.", flush=True)
            continue
        for number, turn in enumerate(conversation["turns"], start=1):
            try:
                answer = post(f"{base_url}/chats/{chat['id']}/ask",
                              {"question": turn["question"], "request_id": str(uuid.uuid4())}, token)
                row = turn_row(conversation, number, turn, answer)
            except ApiError as exc:
                row = {"conversation_id": cid, "turn": number, "question": turn["question"],
                       "error": f"HTTP {exc.status}", "detail": exc.detail}
            except (URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                row = {"conversation_id": cid, "turn": number, "question": turn["question"], "error": type(exc).__name__}
            rows.append(row)
            save(output_path, rows)
            if "error" in row:
                print(f"{cid} tur {number}: HATA ({row['error']}); kalan turlar atlandı.", flush=True)
                break
            used = ",".join(row["used_ticket_ids"]) or "-"
            print(f"{cid} tur {number}: kullanılan={used}; kaynak yetersiz={row['insufficient_context']}; "
                  f"süre={row['elapsed_ms']} ms", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--conversations", type=Path, default=CONVERSATIONS_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE_URL))
    args = parser.parse_args()
    path = args.conversations.resolve()
    conversations = load_conversations(path)
    token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
    if not token:
        parser.error("Önce giriş yapıp APP_ACCESS_TOKEN ortam değişkenini tanımla.")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    name = f"conversation_results_{path.stem}_{now:%Y%m%d_%H%M%S}"
    output_path = output_dir / f"{name}.json"
    metadata = {"started_at": now.isoformat(), "conversations_path": str(path),
                "conversations_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "base_url": args.base_url, "results_path": str(output_path)}
    turns = sum(len(c["turns"]) for c in conversations)
    print(f"{len(conversations)} senaryo, {turns} tur çalıştırılıyor.\n", flush=True)
    rows = run(conversations, _post, args.base_url.rstrip("/"), token, output_path=output_path)
    done = [r for r in rows if "error" not in r]
    metadata.update(finished_at=datetime.now().astimezone().isoformat(), planned_turns=turns,
                    completed_turns=len(done), errors=len(rows) - len(done),
                    expected_source_used=sum(bool(r["expected_source_used"]) for r in done if r["expected_source_used"] is not None),
                    relevant_turns=sum(r["expected_source_used"] is not None for r in done),
                    no_source_passes=sum(bool(r["no_source_pass"]) for r in done if r["no_source_pass"] is not None),
                    no_source_turns=sum(r["no_source_pass"] is not None for r in done),
                    invalid_source_ids=sum(not r["used_sources_valid"] for r in done))
    save(output_dir / f"{name}.meta.json", metadata)
    print(f"\nSonuç: {output_path}\nTamamlanan tur: {len(done)}/{turns}; beklenen kaynak kullanıldı: "
          f"{metadata['expected_source_used']}/{metadata['relevant_turns']}; kaynak yok testi: "
          f"{metadata['no_source_passes']}/{metadata['no_source_turns']}", flush=True)
    if len(done) < turns:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
