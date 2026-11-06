"""RAG adımlarının LangChain Runnable zinciri."""
from __future__ import annotations

from functools import partial
from langchain_core.runnables import RunnableLambda

from conversation import retrieval_question, validate_history
import rag_provider
import rag_repository
from rag_prompts import PROMPT_VERSION, validate_mode
from rag_sources import source_reference


def _embed(question: str, *, history=None) -> dict:
    query = retrieval_question(question, history or [])
    return {'question':question,'vector':rag_provider.embed_question(query)}


def _retrieve(state: dict, *, expertise_mode: str = 'service_desk') -> dict:
    if expertise_mode=='service_desk':
        matches=rag_repository.search_matches(state['vector'])
    else:
        matches=rag_repository.search_matches(state['vector'],expertise_mode=expertise_mode)
    return {'question':state['question'],'matches':matches}


def _answer(state: dict, *, expertise_mode: str = 'service_desk', history=None) -> dict:
    matches=state['matches']
    options = {'expertise_mode': expertise_mode}
    if history:
        options['history'] = history
    result=rag_provider.answer_from_matches(state['question'],matches,**options)
    used=result['used_ticket_ids']
    retrieved=[record['issueid'] for _,record in matches]
    return {
        'answer':result['answer'],'insufficient_context':result['insufficient_context'],
        # Eski alanlar korunur; QA kimlikleri de bu listelerde bulunabilir.
        'used_ticket_ids':used,'retrieved_ticket_ids':retrieved,
        'used_source_ids':used,'retrieved_source_ids':retrieved,
        'sources':[source_reference(r) for _,r in matches if r['issueid'] in used],
        'expertise_mode':expertise_mode,'prompt_version':PROMPT_VERSION,
    }


def build_chain(expertise_mode: str = 'service_desk', *, history=None):
    """Soru -> embedding -> alana uygun ilk üç kaynak -> kaynaklı yanıt."""
    mode=validate_mode(expertise_mode)
    history=validate_history(history)
    return (
        RunnableLambda(partial(_embed,history=history)).with_config(run_name='embed_question')
        | RunnableLambda(partial(_retrieve,expertise_mode=mode)).with_config(run_name='retrieve_sources')
        | RunnableLambda(partial(_answer,expertise_mode=mode,history=history)).with_config(run_name='answer_with_sources')
    )
