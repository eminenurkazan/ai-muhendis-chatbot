"""evaluate_api: soru seti doğrulama, sonuç satırı, hata sonrası devam ve özet. Ağ çağrısı yapılmaz."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evaluate_api as ev


ROOT = Path(__file__).resolve().parents[1]


def answer(retrieved, used, *, insufficient=False, text="Yanıt", elapsed=1000):
    return {"answer": text, "retrieved_ticket_ids": retrieved, "used_ticket_ids": used,
            "insufficient_context": insufficient, "elapsed_ms": elapsed,
            "expertise_mode": "service_desk", "prompt_version": "p", "sources": []}


def question(qid, expected, *, category="service_desk", mode="service_desk"):
    return {"question_id": qid, "question": f"{qid} sorusu", "expected_ticket_ids": expected,
            "expected_insufficient_context": not expected, "category": category, "expertise_mode": mode}


class LoadQuestionsTests(unittest.TestCase):
    def write(self, value):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(value, handle, ensure_ascii=False)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_repository_sets_are_valid(self):
        for name, count in [("evaluation_questions_v1.json", 10), ("evaluation_questions_v2.json", 10),
                            ("evaluation_questions_v3.json", 23)]:
            with self.subTest(name=name):
                self.assertEqual(len(ev.load_questions(ROOT / name)), count)

    def test_v3_covers_required_scenarios(self):
        counts = {}
        for item in ev.load_questions(ROOT / "evaluation_questions_v3.json"):
            counts[item["category"]] = counts.get(item["category"], 0) + 1
            if item["category"] == "windows_server":
                self.assertEqual(item["expertise_mode"], "windows_server")
            if item["category"] == "oracle_db":
                self.assertEqual(item["expertise_mode"], "oracle_db")
            self.assertTrue(item["required_points"])
        self.assertEqual(counts, {"service_desk": 10, "windows_server": 5, "oracle_db": 5, "out_of_scope": 3})

    def test_defaults_mode_and_category_for_old_sets(self):
        item = ev.load_questions(self.write([{"question_id": "a", "question": "q",
                                              "expected_ticket_ids": ["1"], "expected_insufficient_context": False}]))[0]
        self.assertEqual((item["expertise_mode"], item["category"]), ("service_desk", "uncategorized"))

    def test_rejects_invalid_mode_duplicate_and_inconsistent_flag(self):
        good = question("a", ["1"])
        for bad in ([{**good, "expertise_mode": "linux"}], [good, dict(good)],
                    [{**good, "expected_insufficient_context": True}], []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ev.load_questions(self.write(bad))


class ResultRowTests(unittest.TestCase):
    def test_hit_rank_and_validity(self):
        row = ev.result_row(question("a", ["x"]), answer(["y", "x", "z"], ["x"]))
        self.assertTrue(row["top3_hit"])
        self.assertEqual(row["expected_source_rank"], 2)
        self.assertTrue(row["used_sources_valid"])
        self.assertTrue(row["expected_source_used"])
        self.assertFalse(row["used_ids_cited_in_text"])  # bilgi amaçlı; geçerliliği etkilemez

    def test_invented_source_is_invalid(self):
        row = ev.result_row(question("a", ["x"]), answer(["x"], ["x", "uydurma"]))
        self.assertFalse(row["used_sources_valid"])

    def test_no_source_pass_requires_flag_and_no_used_sources(self):
        item = question("n", [], category="out_of_scope")
        self.assertTrue(ev.result_row(item, answer(["a"], [], insufficient=True))["no_source_pass"])
        self.assertFalse(ev.result_row(item, answer(["a"], ["a"], insufficient=False))["no_source_pass"])

    def test_malformed_answer_raises(self):
        with self.assertRaises(ValueError):
            ev.result_row(question("a", ["x"]), {"answer": "t"})


class RunTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name) / "r.json"
        self.meta = Path(folder.name) / "r.meta.json"

    def run_with(self, responses, **options):
        questions = [question("a", ["x"]), question("b", ["y"]), question("n", [], category="out_of_scope")]
        calls = iter(responses)

        def ask(item):
            value = next(calls)
            if isinstance(value, Exception):
                raise value
            return value
        with patch("builtins.print"):
            return ev.run(questions, ask, output_path=self.out, meta_path=self.meta, metadata={}, **options)

    def test_error_is_recorded_and_run_continues(self):
        rows = self.run_with([answer(["x"], ["x"]), ev.ApiError(503, "busy"),
                              answer(["q"], [], insufficient=True)])
        self.assertEqual([r.get("error") for r in rows], [None, "HTTP 503", None])
        self.assertEqual(json.loads(self.out.read_text(encoding="utf-8")), rows)

    def test_stop_on_error(self):
        rows = self.run_with([ev.ApiError(502, "x")], stop_on_error=True)
        self.assertEqual(len(rows), 1)

    def test_summary_by_category(self):
        rows = self.run_with([answer(["x"], ["x"], elapsed=1000), answer(["z", "q", "y"], ["y"], elapsed=3000),
                              answer(["q"], [], insufficient=True, elapsed=2000)])
        summary = ev.summarize(rows)
        desk = summary["by_category"]["service_desk"]
        self.assertEqual((desk["top3_hits"], desk["rank1_hits"], desk["relevant_count"]), (2, 1, 2))
        self.assertEqual(summary["by_category"]["out_of_scope"]["no_source_passes"], 1)
        self.assertEqual(summary["overall"]["mean_elapsed_ms"], 2000)


class FlowTests(unittest.TestCase):
    def test_chat_flow_creates_chat_with_mode_then_asks(self):
        item = question("w", ["k"], category="windows_server", mode="windows_server")
        with patch.object(ev, "_post", side_effect=[{"id": "c1"}, answer(["k"], ["k"])]) as post:
            ev.ask_chat("http://api", "tok", item)
        first, second = post.call_args_list
        self.assertEqual(first.args[0], "http://api/chats")
        self.assertEqual(first.args[1]["expertise_mode"], "windows_server")
        self.assertEqual(second.args[0], "http://api/chats/c1/ask")
        self.assertEqual(set(second.args[1]), {"question", "request_id"})
        self.assertNotIn("expected_ticket_ids", json.dumps(second.args[1]))

    def test_direct_flow_sends_mode_only(self):
        item = question("o", ["k"], category="oracle_db", mode="oracle_db")
        with patch.object(ev, "_post", return_value=answer(["k"], ["k"])) as post:
            ev.ask_direct("http://api", "tok", item)
        self.assertEqual(post.call_args.args[1], {"question": "o sorusu", "expertise_mode": "oracle_db"})


if __name__ == "__main__":
    unittest.main()
