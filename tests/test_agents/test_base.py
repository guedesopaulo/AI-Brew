"""Smoke tests for agents/base.py — no real API calls."""

from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_ollama import ChatOllama
from langgraph.graph.state import CompiledStateGraph

from src.agents.base import create_hello_world_agent
from src.agents.base import get_model


def test_get_model_local_returns_ollama() -> None:
    with patch("src.agents.base.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "local"
        mock_settings.OLLAMA_MODEL = "llama3.2"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        model = get_model()

    assert isinstance(model, ChatOllama)


def test_get_model_cloud_anthropic_returns_provider_string() -> None:
    with patch("src.agents.base.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "dev"
        mock_settings.LLM_PROVIDER = "anthropic"
        mock_settings.LLM_MODEL = "claude-sonnet-4-6"
        model = get_model()

    assert model == "anthropic:claude-sonnet-4-6"


def test_get_model_cloud_openai_returns_provider_string() -> None:
    with patch("src.agents.base.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "dev"
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o"
        model = get_model()

    assert model == "openai:gpt-4o"


def test_create_hello_world_agent_compiles() -> None:
    fake_llm = FakeListChatModel(responses=["hello"])
    with patch("src.agents.base.get_model", return_value=fake_llm):
        agent = create_hello_world_agent()

    assert isinstance(agent, CompiledStateGraph)
