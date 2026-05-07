"""Smoke tests for POST /chat — SSE streaming endpoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def _make_agent_context(events: list[dict]) -> object:
    """Return a patched recipe_agent_context that yields a mock agent."""

    @asynccontextmanager
    async def _ctx(recipe_id: str) -> AsyncGenerator[MagicMock]:
        agent = MagicMock()

        async def _stream_events(inp, config, version):
            for ev in events:
                yield ev

        agent.astream_events = _stream_events
        yield agent

    return _ctx


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app, headers=_auth())


def test_post_chat_returns_event_stream(client: TestClient) -> None:
    ctx = _make_agent_context([])

    with patch("src.endpoints.chat.recipe_agent_context", ctx):
        response = client.post(
            "/chat",
            json={
                "recipe_id": "test-id",
                "message": "help me brew",
                "session_id": "sess-1",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: done" in response.text


def test_post_chat_streams_token_events(client: TestClient) -> None:
    chunk = MagicMock()
    chunk.content = "Hello brewer!"

    events = [
        {"event": "on_chat_model_stream", "data": {"chunk": chunk}},
    ]
    ctx = _make_agent_context(events)

    with patch("src.endpoints.chat.recipe_agent_context", ctx):
        response = client.post(
            "/chat",
            json={
                "recipe_id": "r1",
                "message": "what style should I brew?",
                "session_id": "s1",
            },
        )

    assert "event: token" in response.text
    assert "Hello brewer!" in response.text


def test_post_chat_streams_tool_call_events(client: TestClient) -> None:
    events = [
        {
            "event": "on_tool_start",
            "name": "write_todos",
            "data": {"input": {"todos": ["step 1"]}},
        },
    ]
    ctx = _make_agent_context(events)

    with patch("src.endpoints.chat.recipe_agent_context", ctx):
        response = client.post(
            "/chat",
            json={"recipe_id": "r1", "message": "plan a recipe", "session_id": "s2"},
        )

    assert "event: tool_call" in response.text
    assert "write_todos" in response.text


def test_post_chat_streams_error_on_exception(client: TestClient) -> None:
    @asynccontextmanager
    async def _exploding_ctx(recipe_id: str) -> AsyncGenerator[MagicMock]:
        agent = MagicMock()

        async def _bad_stream(inp, config, version):
            raise RuntimeError("boom")
            yield  # make it a generator

        agent.astream_events = _bad_stream
        yield agent

    with patch("src.endpoints.chat.recipe_agent_context", _exploding_ctx):
        response = client.post(
            "/chat",
            json={"recipe_id": "r1", "message": "crash", "session_id": "s3"},
        )

    assert "event: error" in response.text
    assert "boom" in response.text
    assert "event: done" in response.text


def test_post_chat_handles_anthropic_content_list(client: TestClient) -> None:
    chunk = MagicMock()
    chunk.content = [{"type": "text", "text": "IPA recipe"}, {"type": "other"}]

    events = [
        {"event": "on_chat_model_stream", "data": {"chunk": chunk}},
    ]
    ctx = _make_agent_context(events)

    with patch("src.endpoints.chat.recipe_agent_context", ctx):
        response = client.post(
            "/chat",
            json={"recipe_id": "r1", "message": "suggest a recipe", "session_id": "s4"},
        )

    assert "IPA recipe" in response.text


def test_post_chat_requires_auth() -> None:
    from src.main import app

    no_auth_client = TestClient(app)
    response = no_auth_client.post(
        "/chat",
        json={"recipe_id": "r1", "message": "hi", "session_id": "s5"},
    )
    assert response.status_code == 401
