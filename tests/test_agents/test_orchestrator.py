"""Compile test for orchestrator — no real MCP or LLM calls."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph.state import CompiledStateGraph

from src.agents.orchestrator import recipe_agent_context


def _make_mcp_mock() -> MagicMock:
    """Return a MultiServerMCPClient mock with session context manager."""
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_client.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.anyio
async def test_recipe_agent_context_compiles() -> None:
    fake_llm = FakeListChatModel(responses=["I'll help you brew!"])

    with (
        patch("src.agents.orchestrator.MultiServerMCPClient") as mock_mcp,
        patch("src.agents.orchestrator.load_mcp_tools", new=AsyncMock(return_value=[])),
        patch("src.agents.orchestrator.get_model", return_value=fake_llm),
    ):
        mock_mcp.return_value = _make_mcp_mock()

        async with recipe_agent_context("test-recipe-id") as agent:
            assert isinstance(agent, CompiledStateGraph)


@pytest.mark.anyio
async def test_recipe_agent_context_passes_auth_header() -> None:
    fake_llm = FakeListChatModel(responses=["ok"])

    with (
        patch("src.agents.orchestrator.MultiServerMCPClient") as mock_mcp,
        patch("src.agents.orchestrator.load_mcp_tools", new=AsyncMock(return_value=[])),
        patch("src.agents.orchestrator.get_model", return_value=fake_llm),
        patch("src.agents.orchestrator.settings") as mock_settings,
    ):
        mock_settings.MCP_BASE_URL = "http://localhost:8000"
        mock_settings.LOCAL_API_TOKEN = "secret"
        mock_mcp.return_value = _make_mcp_mock()

        async with recipe_agent_context("abc"):
            pass

        call_kwargs = mock_mcp.call_args[0][0]
        brew_config = call_kwargs["brew"]
        assert brew_config["headers"] == {"Authorization": "Bearer secret"}


@pytest.mark.anyio
async def test_recipe_agent_context_no_auth_header_when_token_none() -> None:
    fake_llm = FakeListChatModel(responses=["ok"])

    with (
        patch("src.agents.orchestrator.MultiServerMCPClient") as mock_mcp,
        patch("src.agents.orchestrator.load_mcp_tools", new=AsyncMock(return_value=[])),
        patch("src.agents.orchestrator.get_model", return_value=fake_llm),
        patch("src.agents.orchestrator.settings") as mock_settings,
    ):
        mock_settings.MCP_BASE_URL = "http://localhost:8000"
        mock_settings.LOCAL_API_TOKEN = None
        mock_mcp.return_value = _make_mcp_mock()

        async with recipe_agent_context("abc"):
            pass

        call_kwargs = mock_mcp.call_args[0][0]
        brew_config = call_kwargs["brew"]
        assert "headers" not in brew_config
