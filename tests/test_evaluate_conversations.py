"""evaluate_conversations: senaryo doğrulama, tek sohbette sıralı sorma ve hata sonrası atlama. Ağ yok."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evaluate_conversations as ec
from evaluate_api import ApiError

ROOT = Path(__file__).resolve().parents[1]


def turn(question, expected, flag=False):
    return {"question": question, "expected_ticket_ids": expected, "expected_insufficient_context": flag}


def conversation(cid="C1", turns=None, mode="service_desk"):
    return {"conversation_id": cid, "expertise_mode": mode,
            "turns": turns or [turn("ilk", ["a"]), turn("takip", ["a"])]}


def answer(used, *, retrieved=None, insufficient=False):
    return {"answer": "yanıt", "used_ticket_ids": used, "retrieved_ticket_ids": retrieved or used or ["x"],
            "insufficient_context": insufficient, "elapsed_ms": 10, "expertise_mode": "service_desk",
            "prompt_version": "p"}


class LoadTests(unittest.TestCase):
    def write(self, value):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(value, handle, ensure_ascii=False)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_repository_set_is_valid(self):
        items = ec.load_conversations(ROOT / "evaluation" / "evaluation_conversations_v1.json")
        self.assertEqual(len(items), 5)
        self.assertEqual(sum(len(i["turns"]) for i in items), 12)

    def test_rejects_bad_sets(self):
        too_long = conversation(turns=[turn("q", ["a"])] * 4)
        single = conversation(turns=[turn("q", ["a"])])
        bad_flag = conversation(turns=[turn("q", ["a"], flag=True), turn("q", ["a"])])
        for bad in ([too_long], [single], [bad_flag], [conversation(mode="linux")],
                    [conversation(), conversation()]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ec.load_conversations(self.write(bad))

    def test_open_ended_first_turn_is_allowed(self):
        item = conversation(turns=[turn("q", ["a"], flag=None), turn("q", ["a"])])
        self.assertEqual(len(ec.load_conversations(self.write([item]))), 1)


class RunTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name) / "r.json"

    def run_with(self, conversations, responses):
        calls = []
        replies = iter(responses)

        def post(url, body, token):
            calls.append((url, body))
            value = next(replies)
            if isinstance(value, Exception):
                raise value
            return value
        with patch("builtins.print"):
            rows = ec.run(conversations, post, "http://api", "tok", output_path=self.out)
        return rows, calls

    def test_turns_are_asked_in_one_chat_without_client_history(self):
        rows, calls = self.run_with([conversation(mode="oracle_db")],
                                    [{"id": "c1"}, answer(["a"]), answer(["a"])])
        self.assertEqual(calls[0][0], "http://api/chats")
        self.assertEqual(calls[0][1]["expertise_mode"], "oracle_db")
        self.assertEqual([c[0] for c in calls[1:]], ["http://api/chats/c1/ask"] * 2)
        for _, body in calls[1:]:
            self.assertEqual(set(body), {"question", "request_id"})  # geçmiş sunucudan okunur
        self.assertEqual([r["turn"] for r in rows], [1, 2])
        self.assertTrue(all(r["expected_source_used"] for r in rows))

    def test_error_skips_remaining_turns_but_not_other_conversations(self):
        rows, _ = self.run_with([conversation("A"), conversation("B")],
                                [{"id": "c1"}, ApiError(503, "busy"), {"id": "c2"}, answer(["a"]), answer(["a"])])
        self.assertEqual([(r["conversation_id"], r["turn"], r.get("error")) for r in rows],
                         [("A", 1, "HTTP 503"), ("B", 1, None), ("B", 2, None)])

    def test_no_source_turn_and_invented_id(self):
        item = conversation(turns=[turn("q", ["a"]), turn("kaynak yok", [], flag=True)])
        rows, _ = self.run_with([item], [{"id": "c"}, answer(["uydurma"], retrieved=["a"]),
                                         answer([], retrieved=["z"], insufficient=True)])
        self.assertFalse(rows[0]["used_sources_valid"])
        self.assertTrue(rows[1]["no_source_pass"])


if __name__ == "__main__":
    unittest.main()
