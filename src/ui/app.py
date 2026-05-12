"""Gradio UI for BrewAgent — chat + live recipe + brew notes panels."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

API_BASE = os.getenv("MCP_BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("LOCAL_API_TOKEN", "test-token")

_AUTH = {"Authorization": f"Bearer {TOKEN}"}
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


async def _fetch_recipe(recipe_id: str) -> dict[str, Any] | None:
    if not recipe_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/recipe/{recipe_id}", headers=_AUTH)
            return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None


def _read_brew_notes(recipe_id: str) -> str:
    path = _REPO_ROOT / "brew_notes" / f"{recipe_id}.md"
    return path.read_text() if path.exists() else "*No brew notes yet.*"


# Yield order matches _outputs:
# chatbot, history_state, session_state, recipe_id_box,
# tool_calls_md, recipe_json, notes_md, msg_box
_YieldTuple = tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    str,
    str,
    str,
    gr.update,
    gr.update,
    gr.update,
]


def _apply_sse_event(
    event_type: str | None,
    data: str,
    history: list[dict[str, str]],
    tool_lines: list[str],
) -> bool:
    """Mutate history/tool_lines in-place. Return True when the stream is done."""
    if event_type == "token":
        history[-1]["content"] += data
    elif event_type == "tool_call":
        tc = json.loads(data)
        tool_lines.append(f"**{tc['name']}** — `{json.dumps(tc.get('input', {}))}`")
    elif event_type == "error":
        history[-1]["content"] = f"Error: {data}"
    elif event_type == "done":
        return True
    return False


async def send_message(
    message: str,
    recipe_id: str,
    history: list[dict[str, str]],
    session_id: str | None,
) -> AsyncGenerator[_YieldTuple]:
    if not session_id:
        session_id = str(uuid.uuid4())
    if not recipe_id:
        recipe_id = str(uuid.uuid4())

    history = [
        *history,
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    tool_lines: list[str] = []

    def _mid_yield() -> _YieldTuple:
        return (
            history,
            history,
            session_id,
            recipe_id,
            "\n\n".join(tool_lines),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    async with httpx.AsyncClient(timeout=180) as client:
        async with client.stream(
            "POST",
            f"{API_BASE}/chat",
            json={"message": message, "recipe_id": recipe_id, "session_id": session_id},
            headers=_AUTH,
        ) as resp:
            event_type: str | None = None
            async for line in resp.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    done = _apply_sse_event(event_type, line[6:], history, tool_lines)
                    if done:
                        break
                    yield _mid_yield()

    yield (
        history,
        history,
        session_id,
        recipe_id,
        "\n\n".join(tool_lines),
        gr.update(value=await _fetch_recipe(recipe_id)),
        gr.update(value=_read_brew_notes(recipe_id)),
        gr.update(value=""),
    )


async def _refresh(recipe_id: str) -> tuple[gr.update, gr.update]:
    return gr.update(value=await _fetch_recipe(recipe_id)), gr.update(
        value=_read_brew_notes(recipe_id)
    )


with gr.Blocks(title="BrewAgent") as demo:
    gr.Markdown("# BrewAgent")

    with gr.Row():
        with gr.Column(scale=6):
            recipe_id_box = gr.Textbox(
                label="Recipe ID",
                placeholder="Leave blank to auto-generate",
            )
            chatbot = gr.Chatbot(label="BrewAgent", layout="bubble", height=500)
            msg_box = gr.Textbox(
                label="Message",
                placeholder="What do you want to brew?",
                lines=2,
            )
            send_btn = gr.Button("Send", variant="primary")
            with gr.Accordion("Tool calls", open=False):
                tool_calls_md = gr.Markdown()

        with gr.Column(scale=4):
            recipe_json = gr.JSON(label="Live Recipe State")
            refresh_btn = gr.Button("Refresh Recipe")
            with gr.Accordion("Brew Notes", open=False):
                notes_md = gr.Markdown("*No brew notes yet.*")

    history_state: gr.State = gr.State([])
    session_state = gr.BrowserState(None)

    _outputs = [
        chatbot,
        history_state,
        session_state,
        recipe_id_box,
        tool_calls_md,
        recipe_json,
        notes_md,
        msg_box,
    ]

    send_btn.click(
        fn=send_message,
        inputs=[msg_box, recipe_id_box, history_state, session_state],
        outputs=_outputs,
    )
    msg_box.submit(
        fn=send_message,
        inputs=[msg_box, recipe_id_box, history_state, session_state],
        outputs=_outputs,
    )
    refresh_btn.click(
        fn=_refresh,
        inputs=[recipe_id_box],
        outputs=[recipe_json, notes_md],
    )


if __name__ == "__main__":
    demo.launch(server_port=7860)
