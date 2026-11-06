"""Bounded, request-local conversation context. No persistence or shared cache."""

MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_MESSAGE_CHARS = 4000
MAX_HISTORY_CHARS = 12000


def validate_history(history=None) -> list[dict[str, str]]:
    if history is None:
        return []
    if not isinstance(history, list) or len(history) > MAX_HISTORY_MESSAGES or len(history) % 2:
        raise ValueError("Geçmiş en fazla 3 tamamlanmış soru–yanıt çifti içermeli.")
    result = []
    for index, message in enumerate(history):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError("Geçmiş mesajında yalnız role ve content alanları bulunmalı.")
        expected = "user" if index % 2 == 0 else "assistant"
        content = message["content"]
        if message["role"] != expected:
            raise ValueError("Geçmiş, kullanıcı ve asistan mesajlarından oluşan tamamlanmış çiftler olmalı.")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_HISTORY_MESSAGE_CHARS:
            raise ValueError("Geçmiş mesajları boş olamaz ve 4000 karakteri aşamaz.")
        result.append({"role": expected, "content": content.strip()})
    if sum(len(item["content"]) for item in result) > MAX_HISTORY_CHARS:
        raise ValueError("Sohbet bağlamı 12000 karakteri aşamaz.")
    return result


def history_from_messages(messages: list[dict]) -> list[dict[str, str]]:
    """Select completed turns only; never send failed or pending questions."""
    pairs = []
    pending = None
    for message in messages:
        if message.get("role") == "user":
            pending = message if message.get("status", "complete") == "complete" else None
        elif message.get("role") == "assistant" and pending is not None:
            pair = [{"role": item["role"], "content": item["content"]} for item in (pending, message)]
            pairs.append(pair)
            pending = None
    selected = []
    size = 0
    for pair in reversed(pairs[-3:]):
        # Keep whole messages and whole turns; don't cut code blocks or sentences.
        cost = sum(len(item["content"]) for item in pair)
        if any(len(item["content"]) > MAX_HISTORY_MESSAGE_CHARS for item in pair) or size + cost > MAX_HISTORY_CHARS:
            break
        selected = pair + selected
        size += cost
    return validate_history(selected)


def retrieval_question(question: str, history: list[dict[str, str]]) -> str:
    if not history:
        return question
    # Use the most recent turn to interpret short replies without another LLM call.
    recent = "\n".join(f"{item['role']}: {item['content'][:1200]}" for item in history[-2:])
    return f"Güncel soru: {question}\n\nÖnceki konuşma bağlamı:\n{recent}"
