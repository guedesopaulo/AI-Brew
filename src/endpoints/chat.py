"""SSE chat endpoint — streams BrewAgent output token by token."""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agents.orchestrator import recipe_agent_context
from src.models.chat import ChatRequest

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def post_chat(body: ChatRequest) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str]:
        try:
            async with recipe_agent_context(body["recipe_id"]) as agent:
                config: RunnableConfig = {
                    "configurable": {"thread_id": body["session_id"]}
                }
                async for event in agent.astream_events(
                    {"messages": [HumanMessage(content=body["message"])]},
                    config=config,
                    version="v2",
                ):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        content = chunk.content
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            # Anthropic format: [{"type": "text", "text": "..."}]
                            text = "".join(
                                b.get("text", "")
                                for b in content
                                if isinstance(b, dict) and b.get("type") == "text"
                            )
                        else:
                            text = ""
                        if text:
                            yield f"event: token\ndata: {text}\n\n"
                    elif kind == "on_tool_start":
                        payload = json.dumps(
                            {
                                "name": event["name"],
                                "input": event["data"].get("input", {}),
                            }
                        )
                        yield f"event: tool_call\ndata: {payload}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {exc!s}\n\n"
        finally:
            yield "event: done\ndata: \n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
