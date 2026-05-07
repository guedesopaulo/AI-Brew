"""Tests for sub-agent definitions."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph.state import CompiledStateGraph

from src.agents.subagents import INGREDIENT_ANALYST
from src.agents.subagents import SENSORY_PROFILER
from src.agents.subagents import STYLE_CONSULTANT


def test_style_consultant_has_required_fields() -> None:
    assert STYLE_CONSULTANT["name"] == "style-consultant"
    assert STYLE_CONSULTANT["description"]
    assert STYLE_CONSULTANT["system_prompt"]
    assert "data/skills/bjcp-styles/" in STYLE_CONSULTANT["skills"]


def test_ingredient_analyst_has_required_fields() -> None:
    assert INGREDIENT_ANALYST["name"] == "ingredient-analyst"
    assert INGREDIENT_ANALYST["description"]
    assert INGREDIENT_ANALYST["system_prompt"]
    skills = INGREDIENT_ANALYST["skills"]
    assert "data/skills/hop-pairing/" in skills
    assert "data/skills/yeast-profiles/" in skills
    assert "data/skills/ingredient-substitutions/" in skills


def test_sensory_profiler_has_required_fields() -> None:
    assert SENSORY_PROFILER["name"] == "sensory-profiler"
    assert SENSORY_PROFILER["description"]
    assert SENSORY_PROFILER["system_prompt"]
    skills = SENSORY_PROFILER["skills"]
    assert "data/skills/hop-pairing/" in skills
    assert "data/skills/yeast-profiles/" in skills


def test_sensory_profiler_has_response_format() -> None:
    from src.models.recipe import SensoryProfile

    assert SENSORY_PROFILER.get("response_format") is SensoryProfile


def _make_mcp_mock() -> MagicMock:
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_client.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.anyio
async def test_orchestrator_compiles_with_subagents() -> None:
    from src.agents.orchestrator import recipe_agent_context

    fake_llm = FakeListChatModel(responses=["ok"])

    with (
        patch("src.agents.orchestrator.MultiServerMCPClient") as mock_mcp,
        patch("src.agents.orchestrator.load_mcp_tools", new=AsyncMock(return_value=[])),
        patch("src.agents.orchestrator.get_model", return_value=fake_llm),
    ):
        mock_mcp.return_value = _make_mcp_mock()

        async with recipe_agent_context("test-id") as agent:
            assert isinstance(agent, CompiledStateGraph)
