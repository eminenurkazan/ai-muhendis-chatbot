"""Mendeley ticket verisinden inceleme adayları bulur ve yorumları gösterir.

Bu araç kaynak CSV dosyasını değiştirmez. Aday sıralaması yalnızca manuel
incelemeyi hızlandırır; bir ticketın onaylandığı anlamına gelmez.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


SOURCE_PATH = Path("sample_utterances.csv")
APPROVED_PATH = Path("tickets_pilot_10.csv")

RESOLUTION_HINTS = (
    "resolved",
    "fixed",
    "working",
    "worked",
    "successful",
    "successfully",
    "solution",
    "closed",
    "closure",
    "restarted",
    "cleared",
    "confirmed",
)


def numeric_value(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def normalize_text(parts: list[str]) -> str:
    text = " ".join(part.strip() for part in parts if part.strip())
    return re.sub(r"\s+", " ", text).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def approved_ids() -> set[str]:
    if not APPROVED_PATH.exists():
        return set()
    return {row["issueid"] for row in read_csv(APPROVED_PATH)}


def group_tickets(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["issueid"]].append(row)
    return grouped


def ticket_comments(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            numeric_value(row["comment_seq"]),
            numeric_value(row["utr_seq"]),
        ),
    )

    comments: list[dict[str, str]] = []
    current_key: tuple[str, str] | None = None
    current_parts: list[str] = []
    current_role = ""

    for row in ordered:
        key = (row["comment_seq"], row["id"])
        if current_key is not None and key != current_key:
            comments.append(
                {
                    "comment_seq": current_key[0],
                    "author_role": current_role,
                    "text": normalize_text(current_parts),
                }
            )
            current_parts = []

        current_key = key
        current_role = row["author_role"]
        current_parts.append(row["actionbody"])

    if current_key is not None:
        comments.append(
            {
                "comment_seq": current_key[0],
                "author_role": current_role,
                "text": normalize_text(current_parts),
            }
        )

    return comments


def candidate_score(comments: list[dict[str, str]]) -> int:
    combined = " ".join(comment["text"].lower() for comment in comments)
    score = sum(1 for hint in RESOLUTION_HINTS if hint in combined)

    if comments and comments[-1]["author_role"] == "reporter":
        score += 2

    if any(
        phrase in combined
        for phrase in (
            "please close",
            "can be closed",
            "issue is resolved",
            "problem is resolved",
            "it is working",
            "thanks for your support",
        )
    ):
        score += 3

    return score


def show_candidates(
    grouped: dict[str, list[dict[str, str]]],
    limit: int,
) -> None:
    already_approved = approved_ids()
    candidates = []

    for issueid, rows in grouped.items():
        if issueid in already_approved:
            continue

        comments = ticket_comments(rows)
        if len(comments) < 2:
            continue

        score = candidate_score(comments)
        if score == 0:
            continue

        final_text = comments[-1]["text"]
        preview = final_text[:120] + ("..." if len(final_text) > 120 else "")
        candidates.append((score, len(comments), issueid, preview))

    candidates.sort(key=lambda item: (-item[0], -item[1], numeric_value(item[2])))

    print(f"Mevcut onaylı ticket: {len(already_approved)}")
    print(f"İncelenebilir aday: {len(candidates)}")
    print("\nÖncelikli adaylar:\n")

    for score, comment_count, issueid, preview in candidates[:limit]:
        print(
            f"{issueid} | puan={score} | yorum={comment_count}\n"
            f"  son yorum: {preview}\n"
        )


def show_ticket(
    grouped: dict[str, list[dict[str, str]]],
    issueid: str,
) -> None:
    rows = grouped.get(issueid)
    if not rows:
        raise SystemExit(f"Ticket bulunamadı: {issueid}")

    print(f"\nTicket {issueid}")
    print("=" * 72)

    for comment in ticket_comments(rows):
        print(
            f"\nYorum {comment['comment_seq']} | "
            f"rol={comment['author_role']}\n"
            f"{comment['text']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--aday-sayisi",
        type=int,
        default=20,
        help="Listelenecek öncelikli aday sayısı.",
    )
    parser.add_argument(
        "--ticket",
        help="Tüm yorumları gösterilecek ticket kimliği.",
    )
    args = parser.parse_args()

    grouped = group_tickets(read_csv(SOURCE_PATH))

    if args.ticket:
        show_ticket(grouped, args.ticket)
    else:
        show_candidates(grouped, args.aday_sayisi)


if __name__ == "__main__":
    main()
