"""RAG adımlarının LangChain Runnable zinciri."""

from __future__ import annotations

from langchain_core.runnables import RunnableLambda

import rag_provider
import rag_repository


def _embed(question: str) -> dict:
    return {"question": question, "vector": rag_provider.embed_question(question)}


def _retrieve(state: dict) -> dict:
    matches = rag_repository.search_matches(state["vector"])
    return {"question": state["question"], "matches": matches}


def _answer(state: dict) -> dict:
    matches = state["matches"]
    result = rag_provider.answer_from_matches(state["question"], matches)
    return {
        "answer": result["answer"],
        "used_ticket_ids": result["used_ticket_ids"],
        "insufficient_context": result["insufficient_context"],
        "retrieved_ticket_ids": [record["issueid"] for _, record in matches],
    }


def build_chain():
    """Soru -> embedding -> ilk üç kaynak -> kaynak kimliği denetlenmiş yanıt."""
    return (
        RunnableLambda(_embed).with_config(run_name="embed_question")
        | RunnableLambda(_retrieve).with_config(run_name="retrieve_tickets")
        | RunnableLambda(_answer).with_config(run_name="answer_with_sources")
    )
