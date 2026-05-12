"""SSE chat endpoint — streams BrewAgent output token by token."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agents.orchestrator import recipe_agent_context
from src.config import settings
from src.models.chat import ChatRequest
from src.resources.recipe import ensure_recipe

router = APIRouter(tags=["chat"])


def _stream_text(event: dict[str, Any]) -> str:
    """Extract streamed text from an on_chat_model_stream event."""
    content = event["data"]["chunk"].content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


async def _yield_events(
    agent_events: AsyncGenerator[Any],
) -> AsyncGenerator[str]:
    """Yield SSE token/tool_call strings from an astream_events generator."""
    async for event in agent_events:
        kind = event["event"]
        if kind == "on_chat_model_stream":
            text = _stream_text(event)
            if text:
                yield f"event: token\ndata: {text}\n\n"
        elif kind == "on_tool_start":
            payload = json.dumps(
                {"name": event["name"], "input": event["data"].get("input", {})}
            )
            yield f"event: tool_call\ndata: {payload}\n\n"


@router.post("/chat")
async def post_chat(body: ChatRequest) -> StreamingResponse:
    await ensure_recipe(body["recipe_id"], settings.DB_PATH)

    async def event_stream() -> AsyncGenerator[str]:
        stream_ok = False
        try:
            async with recipe_agent_context(body["recipe_id"]) as agent:
                config: RunnableConfig = {
                    "configurable": {"thread_id": body["session_id"]}
                }
                async for chunk in _yield_events(
                    agent.astream_events(
                        {"messages": [HumanMessage(content=body["message"])]},
                        config=config,
                        version="v2",
                    )
                ):
                    yield chunk
                stream_ok = True
        except Exception as exc:
            # ExceptionGroup = LangGraph/MCP teardown noise, not a real error.
            if not isinstance(exc, BaseExceptionGroup) and not stream_ok:
                yield f"event: error\ndata: {exc!s}\n\n"
        finally:
            yield "event: done\ndata: \n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
