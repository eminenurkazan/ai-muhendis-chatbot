"""RAG adımlarının LangChain Runnable zinciri."""

from __future__ import annotations

from functools import partial

from langchain_core.runnables import RunnableLambda

import rag_provider
import rag_repository
from rag_prompts import PROMPT_VERSION, validate_mode


def _embed(question: str) -> dict:
    return {"question": question, "vector": rag_provider.embed_question(question)}


def _retrieve(state: dict) -> dict:
    matches = rag_repository.search_matches(state["vector"])
    return {"question": state["question"], "matches": matches}


def _answer(state: dict, *, expertise_mode: str = "service_desk") -> dict:
    matches = state["matches"]
    result = rag_provider.answer_from_matches(state["question"], matches, expertise_mode=expertise_mode)
    return {
        "answer": result["answer"],
        "used_ticket_ids": result["used_ticket_ids"],
        "insufficient_context": result["insufficient_context"],
        "retrieved_ticket_ids": [record["issueid"] for _, record in matches],
        "expertise_mode": expertise_mode,
        "prompt_version": PROMPT_VERSION,
    }


def build_chain(expertise_mode: str = "service_desk"):
    """Soru -> embedding -> ilk üç kaynak -> kaynak kimliği denetlenmiş yanıt."""
    mode = validate_mode(expertise_mode)
    return (
        RunnableLambda(_embed).with_config(run_name="embed_question")
        | RunnableLambda(_retrieve).with_config(run_name="retrieve_tickets")
        | RunnableLambda(partial(_answer, expertise_mode=mode)).with_config(run_name="answer_with_sources")
    )
