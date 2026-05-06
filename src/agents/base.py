"""LLM factory and base agent builder."""

from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from src.config import settings


def get_model() -> str | BaseChatModel:
    # Local: ChatOllama instance (Ollama has no provider:model string support).
    # Cloud: provider string resolved by langchain via os.environ.
    if settings.ENVIRONMENT == "local":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL
        )

    return f"{settings.LLM_PROVIDER}:{settings.LLM_MODEL}"


def create_hello_world_agent() -> CompiledStateGraph[Any, Any, Any, Any]:
    return create_deep_agent(
        model=get_model(),
        system_prompt=(
            "You are a helpful assistant. "
            "Always plan with write_todos before answering."
        ),
    )
