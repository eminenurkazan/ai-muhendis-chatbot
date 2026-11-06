"""Bulut çağrısı yapmadan RAG zincirinin davranışını sınar."""

import unittest
from unittest.mock import patch

import rag_service
import rag_ticket_pilotu as rag


class RagFlowTests(unittest.TestCase):
    def test_chain_keeps_source_ids_and_response_shape(self):
        matches = [(0.9, {"issueid": "1007444.0"}), (0.5, {"issueid": "1006809.0"})]
        answer = {
            "answer": "UAT ortamında doğrulandı. Ticket: 1007444.0",
            "used_ticket_ids": ["1007444.0"],
            "insufficient_context": False,
        }
        with (
            patch("rag_provider.embed_question", return_value=[0.1, 0.2]) as embed,
            patch("rag_repository.search_matches", return_value=matches) as search,
            patch("rag_provider.answer_from_matches", return_value=answer) as generate,
        ):
            result = rag_service.ask_question("  UAT sorusu  ")
        embed.assert_called_once_with("UAT sorusu")
        search.assert_called_once_with([0.1, 0.2])
        generate.assert_called_once_with("UAT sorusu", matches, expertise_mode="service_desk")
        self.assertEqual(result["retrieved_ticket_ids"], ["1007444.0", "1006809.0"])
        self.assertEqual(result["used_ticket_ids"], ["1007444.0"])
        self.assertGreaterEqual(result["elapsed_ms"], 0)

    def test_empty_question_is_rejected_before_cloud_call(self):
        with patch("rag_provider.embed_question") as embed:
            with self.assertRaises(ValueError):
                rag_service.ask_question("  ")
        embed.assert_not_called()

    def test_unretrieved_source_is_rejected_by_existing_parser(self):
        raw = '{"answer":"Ticket: 9999999.0", "used_ticket_ids":["9999999.0"], "insufficient_context":false}'
        with self.assertRaises(rag.RagError):
            rag.parse_answer(raw, [(0.9, {"issueid": "1007444.0"})])


    def test_readable_answer_keeps_validated_source_metadata(self):
        import json
        source_id = "serverfault:q1166382:a1166413"
        raw = json.dumps({"answer": "İlgili kaynakta belirtilen adımı bu kapsamda inceleyebilirsin.",
                          "used_ticket_ids": [source_id], "insufficient_context": False})
        result = rag.parse_answer(raw, [(0.9, {"issueid": source_id})])
        self.assertNotIn(source_id, result["answer"])
        self.assertEqual(result["used_ticket_ids"], [source_id])

    def test_readable_answer_still_rejects_inconsistent_source_metadata(self):
        import json
        for ids, insufficient in (([], False), (["known-id"], True), (["known-id", "known-id"], False)):
            with self.subTest(ids=ids, insufficient=insufficient):
                raw = json.dumps({"answer": "Kısa açıklama.", "used_ticket_ids": ids,
                                  "insufficient_context": insufficient})
                with self.assertRaises(rag.RagError):
                    rag.parse_answer(raw, [(0.9, {"issueid": "known-id"})])

if __name__ == "__main__":
    unittest.main()
