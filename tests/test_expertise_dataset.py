"""Dış ağ ve model çağrısı olmadan QA eşleştirme/izlenebilirlik kontrolleri."""

import unittest

from data_sources.stackexchange_dataset import make_record, text_from_html


class ExpertiseDatasetTests(unittest.TestCase):
    def pair(self):
        question = {"question_id": 10, "accepted_answer_id": 20, "title": "Oracle example",
            "body": "<p>" + "Question with enough context. " * 5 + "</p>", "link": "https://dba.stackexchange.com/q/10",
            "tags": ["oracle"], "content_license": "CC BY-SA 4.0",
            "owner": {"display_name": "Question author", "link": "https://dba.stackexchange.com/users/1"}}
        answer = {"answer_id": 20, "question_id": 10, "is_accepted": True, "score": 2,
            "body": "<p>" + "Answer with enough explanation. " * 8 + "</p>", "content_license": "CC BY-SA 4.0",
            "owner": {"display_name": "Answer author", "link": "https://dba.stackexchange.com/users/2"}}
        return question, answer

    def test_keeps_code_and_decodes_html(self):
        text = text_from_html('<p>Compare &lt; 5</p><pre><code>SELECT 1;\nSELECT 2;</code></pre>')
        self.assertIn("Compare < 5", text)
        self.assertIn("```\nSELECT 1;\nSELECT 2;\n```", text)

    def test_rejects_wrong_or_unaccepted_answer(self):
        question, answer = self.pair()
        answer["answer_id"] = 99
        record, reason = make_record("dba", question, answer, ["sql_performance"])
        self.assertIsNone(record)
        self.assertEqual(reason, "answer_pair_mismatch")

    def test_requires_license_and_author_attribution(self):
        question, answer = self.pair()
        answer.pop("content_license")
        self.assertIsNone(make_record("dba", question, answer, ["sql_performance"])[0])

    def test_candidates_are_pending_and_acceptance_is_not_resolution_confirmation(self):
        question, answer = self.pair()
        record, _ = make_record("dba", question, answer, ["sql_performance"])
        self.assertEqual(record["review_status"], "pending")
        self.assertEqual(record["index_status"], "pending")
        self.assertIsNone(record["resolution_confirmed"])
        self.assertTrue(record["answer_accepted"])
        self.assertIn("/a/20", record["answer_url"])
        self.assertEqual(record["answer_author"]["name"], "Answer author")


if __name__ == "__main__":
    unittest.main()
