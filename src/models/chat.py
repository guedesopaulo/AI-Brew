"""Chat request/response models."""

from typing import Literal
from typing import TypedDict


class ChatRequest(TypedDict):
    recipe_id: str
    message: str
    session_id: str  # maps to LangGraph thread_id


class HistoryMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
