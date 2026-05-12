"""Chat request/response models."""

from typing import TypedDict


class ChatRequest(TypedDict):
    recipe_id: str
    message: str
    session_id: str  # maps to LangGraph thread_id
