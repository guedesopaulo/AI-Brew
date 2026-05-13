# BrewAgent — Implementation Plan

## Context

This repo is a template FastAPI + FastMCP skeleton. The goal is to build a beer recipe assistant (Brewfather/BeerSmith-like) powered by deepagents: a planning-first, context-offloading, sub-agent-orchestrating LangGraph harness. The beer domain is intentionally chosen because it mixes deterministic calculations (OG, IBU, SRM) with fuzzy sensory prediction — a good stress test for agent coordination. The UI is Gradio (agent chat + live recipe panel), with FastAPI as the backend. This plan covers Phase 0–2 in detail and Phase 3–6 as sketches.

**User answers:** LLM = ENVIRONMENT-based (Ollama local, Anthropic cloud); UI = Gradio; ingredient data = static JSON; scope = Phase 0–2 deep.

---

## The 4 Core Principles (always evaluate every decision against these)

| # | Principle | What it means in practice here |
|---|---|---|
| 1 | **Planning-first execution** | The orchestrator calls `write_todos` before touching any recipe parameter. No tool call happens without a prior plan step. Human-in-the-loop (Phase 6) extends this — destructive actions wait for explicit approval. |
| 2 | **Context offloading** | The live recipe state is never stuffed into the prompt. The agent reads/writes it via MCP tools (recipe in DB). The agent can use `write_file`/`read_file` built-in tools to offload working notes to `data/brew_notes/{recipe_id}.md`. |
| 3 | **Task delegation** | The orchestrator is kept narrow: it plans and routes. Specialist sub-agents (Style Consultant, Ingredient Analyst, Sensory Profiler) each get only the slice of context they need. |
| 4 | **Prompting still matters** | Every agent and sub-agent has a tightly scoped system prompt. The orchestrator prompt enforces the plan-first rule. Sub-agent prompts define strict output contracts (structured JSON). Good coordination is mostly good prompts. |

> **Decision rule:** Before adding any feature, ask which principle it serves. If it doesn't clearly reinforce one of the four, it probably doesn't belong in the agent layer.

---

## Corrections vs. original plan.md

| Item | Original | Revised |
|---|---|---|
| deepagents version | `>=0.5.5` | `>=0.5.7` (latest stable as of 2026-05-06) |
| Subagent API | `task` tool spawning at runtime | Subagents defined upfront as dicts in `create_deep_agent(subagents=[...])` — the `task` tool picks them by name |
| LLM provider | `LLM_PROVIDER` config toggle | Derived from `ENVIRONMENT`: Ollama for local, Anthropic for cloud (no extra setting needed) |
| MCP auth | expose `/mcp` publicly | Pass `LOCAL_API_TOKEN` in `MultiServerMCPClient` headers; `/mcp` stays protected |
| Observability | LangSmith | Langfuse — already in production at fcx-atlantis; `LangfuseManager` singleton with graceful no-op |
| Gradio phase | Phase 4 separate | Add `gradio` dep now; implement `src/ui/app.py` in Phase 4 |
| include_router ordering | implicit | Recipe router must be included **before** `FastMCP.from_fastapi()` in main.py |
| `memory` param purpose | context offload of recipe state | AGENTS.md-style instruction files only — recipe state lives in DB, accessed via MCP tools |
| `get_tools()` call | `client.get_tools()` | `await client.get_tools()` — the method is async |
| MCP client lifecycle | simple factory returns graph | `asynccontextmanager` keeps client open for the entire agent run; tools become invalid when context exits |
| Session persistence (Phase 2) | no checkpointer | `MemorySaver()` for in-process multi-turn sessions; Phase 5 upgrades to `SqliteSaver` |
| Agent file operations (Phase 2) | needed `FilesystemBackend` | NOT needed in Phase 2 — `StateBackend` (default) stores files in agent state, `MemorySaver` checkpoints them. `FilesystemBackend` added in Phase 4 for Gradio to read files externally. |
| Streaming method | `astream_events(version="v2")` | Confirmed correct for token-level SSE. Alternative: `astream(stream_mode="messages")`. The build-from-scratch repo uses `astream(stream_mode=["updates","values"])` for node-level updates — that's insufficient for real-time token streaming. |
| `MultiServerMCPClient` lifecycle (0.2.2) | `async with MultiServerMCPClient(...) as client` | Context manager removed in 0.1.0. Use `client.session("brew")` + `load_mcp_tools(session)` to keep the session alive for the full agent run. |
| FastMCP transport | `"streamable-http"` (hyphen) | `"streamable_http"` (underscore) for `StreamableHttpConnection`. FastMCP `transport="http"` = Streamable HTTP protocol, NOT SSE. |
| FastMCP tool names | `post_recipe`, `get_recipe_by_id` | Auto-generated with route suffix: `post_recipe_recipe_post`, `get_recipe_by_id_recipe`, `patch_recipe_recipe`, `get_recipes_recipes_get`. System prompt must use exact names. |
| `FilesystemBackend` import | `from deepagents import FilesystemBackend` | `from deepagents.backends import FilesystemBackend` — top-level import does not exist in 0.5.7. |
| Gradio version | `>=5.0.0` in pyproject | Installed is **6.14.0**. `gr.Chatbot(type="messages")` does NOT exist — Gradio 6 uses message dicts natively with no `type` param. |

---

## Phase 0 — Foundations ✅ COMPLETE

**Delivered:**
- `pyproject.toml`: `deepagents>=0.5.7`, `langchain-anthropic`, `langchain-openai`, `langchain-ollama`, `langchain-mcp-adapters`, `aiosqlite`, `gradio`
- `src/config.py`: LLM settings (`LLM_PROVIDER`, `LLM_MODEL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_*`), storage (`DB_PATH`, `MCP_BASE_URL`), Langfuse fields. API keys propagated to `os.environ` at startup.
- `src/agents/base.py`: `get_model()` returns `ChatOllama` for local or `"provider:model"` string for cloud. `create_hello_world_agent()` uses `create_deep_agent`. MCP client headers pattern for auth forwarding documented here.
- `tests/test_agents/test_base.py`: 4 tests, all passing. No real API calls.

**Key implementation detail:** `ChatAnthropic`/`ChatOpenAI` are never instantiated directly — cloud uses the `"provider:model"` string passed to `create_deep_agent`, avoiding pydantic v1 mypy incompatibilities.

---

## Phase 1 — Recipe Domain (REST + calculations) ✅ COMPLETE

**Delivered:**
- `src/models/recipe.py`: TypedDicts — `Fermentable`, `Hop`, `Yeast`, `CalculatedStats`, `Recipe`, `RecipePatch(total=False)`, `RecipeWithStats`, `SensoryProfile`
- `src/data/fermentables.json` (~50 entries), `hops.json` (~40), `yeasts.json` (~22), `styles.json` (~34 BJCP styles)
- `src/service/recipe.py`: Pure calc functions — `calc_og` (PPG formula), `calc_ibu_tinseth` (Tinseth), `calc_srm_morey` (Morey), `calc_fg`, `calc_abv`, `calculate_stats`
- `src/resources/recipe.py`: aiosqlite CRUD — `init_db`, `create_recipe`, `get_recipe`, `update_recipe`, `list_recipes`
- `src/endpoints/recipe.py`: 4 routes — `POST /recipe`, `GET /recipe/{id}` (with stats), `PATCH /recipe/{id}`, `GET /recipes`
- `src/main.py`: recipe router included before `FastMCP.from_fastapi()`, `init_db` in lifespan
- `tests/test_recipe_service.py`: 22 table-driven tests
- `tests/test_recipe_endpoints.py`: 7 smoke tests (resource layer mocked)

**Concept explored:** FastMCP auto-generates MCP tools from every FastAPI route — zero extra work.

---

## Phase 2 — Orchestrator Agent + Chat Endpoint ✅ COMPLETE

**Delivered:**
- `src/models/chat.py`: `ChatRequest` TypedDict (`recipe_id`, `message`, `session_id`)
- `src/agents/orchestrator.py`: `recipe_agent_context` asynccontextmanager; `MemorySaver` singleton; `client.session("brew")` + `load_mcp_tools()` to keep session alive during agent execution
- `src/endpoints/chat.py`: `POST /chat` SSE endpoint; `astream_events(version="v2")`; handles `str` and Anthropic `list[dict]` content; events: `token`, `tool_call`, `done`, `error`
- `src/main.py`: chat router added; `brew_notes/` dir created in lifespan
- `tests/test_agents/test_orchestrator.py`: 3 compile tests (mocked MCP + FakeListChatModel)
- `tests/test_chat_endpoint.py`: 6 SSE tests

**Verified working manually:** agent reads recipe via MCP, builds full IPA ingredient list, patches DB, returns calculated stats (OG, IBU, SRM, ABV) in one turn.

**Key corrections discovered during implementation:**
- `langchain-mcp-adapters` 0.2.2 removed context manager from `MultiServerMCPClient` — use `client.session("brew")` + `load_mcp_tools(session)` to keep session alive
- FastMCP `transport="http"` = Streamable HTTP (not SSE) — client must use `StreamableHttpConnection`
- FastMCP auto-generates verbose tool names: `post_recipe_recipe_post`, `get_recipe_by_id_recipe`, `patch_recipe_recipe`, `get_recipes_recipes_get` — system prompt must reference exact names
- `write_todos` planning not reliably enforced by prompt alone — needs stronger framing in Phase 3

**Goal:** Agent interprets natural-language recipe requests, plans via `write_todos`, reads/modifies recipe via MCP tools, streams back via SSE.

### Key deepagents API facts (confirmed from source)

- `create_deep_agent(model, tools, system_prompt, checkpointer, memory, ...)` — `tools` are merged with built-ins (`write_todos`, `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`, `execute`, `task`)
- `memory: list[str]` — paths to AGENTS.md-style instruction files; loaded into system prompt at startup. NOT for recipe state (that stays in DB).
- `checkpointer: Checkpointer | None` — passed to LangGraph. Use `MemorySaver()` for in-process sessions.
- `MultiServerMCPClient.get_tools()` is **async** — must `await` it.
- `FilesystemBackend(root_dir=Path("."))` — needed for built-in file tools to write to disk. Without it, `StateBackend` (default) operates on in-memory ephemeral state.

### 2a. Orchestrator — `src/agents/orchestrator.py`

The MCP client MUST stay alive while the agent runs — tools become invalid when the context manager exits. Use an `asynccontextmanager` that yields the compiled agent:

```python
SYSTEM_PROMPT = """
You are an expert homebrewer assistant.
Before modifying any recipe parameter, ALWAYS call write_todos with a
numbered plan. Each step must reference a specific MCP tool call.
Only proceed after the plan is complete. Never skip planning.

The MCP tool names available to you are:
- post_recipe       — create a new recipe
- get_recipe_by_id  — read a recipe with calculated stats
- patch_recipe      — update recipe fields
- get_recipes       — list all recipes

For working notes, use write_file to save context to
brew_notes/{recipe_id}.md instead of keeping it in the conversation.
"""

_checkpointer = MemorySaver()  # module-level singleton; survives across requests

@asynccontextmanager
async def recipe_agent_context(
    recipe_id: str,
) -> AsyncGenerator[CompiledStateGraph[Any, Any, Any, Any], None]:
    mcp_config: dict[str, Any] = {
        "url": f"{settings.MCP_BASE_URL}/mcp",
        "transport": "streamable-http",
    }
    if settings.LOCAL_API_TOKEN:
        mcp_config["headers"] = {
            "Authorization": f"Bearer {settings.LOCAL_API_TOKEN}"
        }
    async with MultiServerMCPClient({"brew": mcp_config}) as client:
        tools = await client.get_tools()
        agent = create_deep_agent(
            model=get_model(),
            tools=tools,
            system_prompt=SYSTEM_PROMPT.format(recipe_id=recipe_id),
            checkpointer=_checkpointer,
            # StateBackend (default) — file writes go into agent state dict,
            # which MemorySaver checkpoints. Files persist across /chat calls
            # for the same session_id without needing FilesystemBackend.
            # Phase 4 adds FilesystemBackend when Gradio needs to read the files.
        )
        yield agent
```

**Why module-level `_checkpointer`:** `MemorySaver` stores conversation history AND the full agent state (including the virtual `files` dict) between requests. The `StateBackend` (default) stores agent file writes in this state dict — so `write_file` calls persist across `/chat` requests for the same `session_id`. No `FilesystemBackend` needed in Phase 2.

**Virtual filesystem insight (from `deep-agents-from-scratch` source):** deepagents' built-in `write_file` tool stores files as a dict in agent state (`state["files"]["path"] = content`), not on disk. `MemorySaver` checkpoints this dict between requests. `FilesystemBackend` is only needed when files must be accessible OUTSIDE the agent (e.g., Gradio UI reading them directly — Phase 4).

**FastMCP tool names:** FastMCP derives tool names from route function names: `post_recipe`, `get_recipe_by_id`, `patch_recipe`, `get_recipes`. These are the names the system prompt must reference.

### 2b. Chat request model — `src/models/chat.py`

```python
class ChatRequest(TypedDict):
    recipe_id: str
    message: str
    session_id: str  # maps to LangGraph thread_id; reserved for Phase 5 persistence
```

### 2c. Chat endpoint — `src/endpoints/chat.py`

```python
@router.post("/chat")
async def post_chat(body: ChatRequest) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async with recipe_agent_context(body["recipe_id"]) as agent:
                config = {"configurable": {"thread_id": body["session_id"]}}
                async for event in agent.astream_events(
                    {"messages": [HumanMessage(content=body["message"])]},
                    config=config,
                    version="v2",
                ):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            text = chunk.content if isinstance(chunk.content, str) \
                                   else chunk.content[0].get("text", "")
                            if text:
                                yield f"event: token\ndata: {text}\n\n"
                    elif kind == "on_tool_start":
                        payload = json.dumps({
                            "name": event["name"],
                            "input": event["data"].get("input", {}),
                        })
                        yield f"event: tool_call\ndata: {payload}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {exc!s}\n\n"
        finally:
            yield "event: done\ndata: \n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**SSE event contract:**
| event | data | when |
|---|---|---|
| `token` | raw text chunk | streamed LLM output |
| `tool_call` | JSON `{name, input}` | agent starts a tool |
| `done` | *(empty)* | stream complete |
| `error` | error string | exception during streaming |

**Note:** `/chat` stays protected by `BearerTokenMiddleware`. Gradio (Phase 4) passes the token in its HTTP client. Tests pass `Authorization: Bearer test-token`.

### 2d. Wire into main.py

```python
from src.endpoints.chat import router as chat_router

# Include before FastMCP:
app.include_router(chat_router)
```

### 2e. Tests

**`tests/test_agents/test_orchestrator.py`** — compile test only (no real MCP or LLM):
```python
@pytest.mark.anyio
async def test_recipe_agent_context_compiles():
    with patch("src.agents.orchestrator.MultiServerMCPClient") as mock_mcp:
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_mcp.return_value)
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_mcp.return_value.get_tools = AsyncMock(return_value=[])
        with patch("src.agents.orchestrator.get_model", return_value=FakeListChatModel(...)):
            async with recipe_agent_context("test-id") as agent:
                assert isinstance(agent, CompiledStateGraph)
```

**`tests/test_chat_endpoint.py`** — mock the entire orchestrator context:
```python
def test_post_chat_streams_sse(client):
    with patch("src.endpoints.chat.recipe_agent_context") as mock_ctx:
        # mock astream_events to yield one token event
        ...
        response = client.post("/chat", json={...}, headers=_auth())
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
```

### 2f. Considerations from official deepagents examples

After reviewing the official examples (`deep_research`, `text-to-sql-agent`, `async-subagent-server`, `nvidia_deep_agent`):

**Confirmed — aligns with plan:**
- `FilesystemBackend(root_dir=path)` is the standard for on-disk file operations (text-to-sql uses it)
- Subagent dict pattern with `name`, `description`, `system_prompt`, `tools` is confirmed
- `{"messages": [{"role": "user", "content": "..."}]}` is the standard input format
- Module-level `MemorySaver` singleton is the right pattern for in-process sessions

**Notable difference — FastAPI integration style:**
The `async-subagent-server` example uses **Agent Protocol** (fire-and-forget + polling), NOT SSE:
- `POST /threads` → create thread
- `POST /threads/{id}/runs` → start background task, return `run_id`
- `GET /threads/{id}/runs/{run_id}` → poll status
- `GET /threads/{id}` → fetch final messages

This is the framework's "official" FastAPI pattern. Our SSE approach is different but deliberate: Gradio needs real-time streaming, and `astream_events` from LangGraph supports it. The Agent Protocol pattern is documented as an option for Phase 5+ if we expose the agent externally.

**Novel pattern — self-referential MCP:**
No example shows an agent connecting back to its own FastAPI server's `/mcp` endpoint via `MultiServerMCPClient`. All examples either use `mcp.json` (external MCP servers) or no MCP at all. Our pattern is uncharted — the `asynccontextmanager` design is the correct solution, but this needs careful manual testing (verify Phase 1 MCP check before starting Phase 2 implementation).

**FastMCP-generated tool names:**
FastMCP derives tool names from route function names. Our routes will generate:
- `post_recipe` → creates a recipe
- `get_recipe_by_id` → reads with stats
- `patch_recipe` → partial update
- `get_recipes` → list

The orchestrator system prompt must reference these exact names when instructing the agent to plan steps.

**Skills directory (Phase 3 opportunity):**
Examples use `skills=["./skills/"]` for just-in-time domain knowledge files (e.g., `skills/bjcp/SKILL.md`). In Phase 3, this is cleaner than injecting BJCP style ranges into the subagent prompt — the agent reads the skill file on demand via `read_file`.

**Gaps resolved:**
| Gap | Resolution |
|---|---|
| `client.get_tools()` was sync | Must `await client.get_tools()` |
| MCP context exits before agent runs | `asynccontextmanager` wraps the entire agent invocation |
| `memory=` described as recipe state offload | It's AGENTS.md instructions only; recipe state stays in DB |
| No `FilesystemBackend` | Required for `write_file`/`read_file` tools to hit disk |
| No checkpointer | `MemorySaver()` singleton for in-process multi-turn sessions |
| `data/brew_notes/` directory | Created in lifespan |
| Input format unspecified | `{"messages": [{"role": "user", "content": "..."}]}` |
| Token chunk content type | May be `str` or `list[dict]` — handle both |

**Concepts explored:** Planning-first via `write_todos`; MCP tool calls as the recipe state interface (never in prompt); SSE streaming for real-time agent output; `MemorySaver` for session continuity.

---

## Phase 3 — Sub-agents + Skills ✅ COMPLETE

**Delivered:**
- `data/skills/bjcp-styles/SKILL.md` — 37 BJCP styles with OG/IBU/SRM/ABV ranges, key malts, hops, yeast per style
- `data/skills/hop-pairing/SKILL.md` — 40 hops by flavor category + style pairing guide + dry hop rate table
- `data/skills/yeast-profiles/SKILL.md` — 22 strains with attenuation, temp ranges, quick selection table
- `data/skills/ingredient-substitutions/SKILL.md` — malt, hop, and yeast substitution tables
- `src/agents/subagents.py`: `STYLE_CONSULTANT`, `INGREDIENT_ANALYST`, `SENSORY_PROFILER` — all with `tools=[]`; `SENSORY_PROFILER` uses `response_format=SensoryProfile`
- `src/agents/orchestrator.py`: updated with `subagents=`, `skills=["data/skills/"]`, system prompt lists sub-agents by name
- `src/endpoints/recipe.py`: `GET /recipe/{id}/profile` — delegates to sensory-profiler, scans all messages in reverse for valid SensoryProfile JSON
- `tests/test_agents/test_subagents.py`: 5 tests — required keys, response_format, orchestrator compiles with subagents
- `tests/test_recipe_endpoints.py`: 4 profile tests — happy path (JSON in middle message), 404, no-profile-found 422, thread_id assertion

**Key corrections discovered during implementation:**
- `response_format=SensoryProfile` on sub-agent makes deepagents return the JSON in a **ToolMessage**, not the final AIMessage. The final AIMessage is often `content=""` after the orchestrator considers delegation complete. Fix: scan all messages in reverse for the first dict containing `{aroma, flavor, mouthfeel, appearance}` keys.
- `thread_id` must be passed to `agent.ainvoke` even for one-shot profile calls. `MemorySaver` raises `ValueError` at runtime without it. Pattern: `f"profile-{recipe_id}"`.
- `tools=[]` must be explicitly set on sub-agents — `NotRequired` defaults to inheriting parent tools, which would give sub-agents access to all MCP tools.
- `SubAgent` confirmed fields: `name`, `description`, `system_prompt`, `tools` (NotRequired), `model` (NotRequired), `skills` (NotRequired), `response_format` (NotRequired).
- Architectural note deferred: `HumanMessage` import in `src/endpoints/recipe.py` leaks agent internals into the endpoints layer. Fix when a dedicated `invoke_sensory_profile()` wrapper is added to the orchestrator module (Phase 4/5).

---

## Phase 4 — Gradio UI

**Goal:** Visual interface — chat on the left, live recipe + brew notes panel on the right. Connects to existing `/chat` SSE and `/recipe/{id}` REST endpoints. Also adds `FilesystemBackend` so `write_file` persists brew notes to disk and the UI can display them after each turn.

### 4a. Dependencies

`gradio>=5.0.0` (installed: **6.14.0**) and `httpx` (0.28.1) already present. No new deps needed.

**Confirmed Gradio 6 API facts (verified against installed version):**
- `gr.Chatbot()` — no `type` parameter needed; message format is `[{"role": "user"|"assistant", "content": "..."}]` natively in Gradio 6
- `gr.update(value=...)` still works ✅
- Streaming: `async def` generator wired to `.click()` or `.submit()` — Gradio 6 handles the async event loop automatically
- No `queue()` call needed (removed in Gradio 5+)

### 4b. Layout — `src/ui/app.py`

```
gr.Blocks(title="BrewAgent")
├── gr.Row
│   ├── gr.Column(scale=6) — Chat panel
│   │   ├── gr.Textbox(label="Recipe ID")
│   │   ├── gr.Chatbot(label="BrewAgent", layout="bubble")
│   │   ├── gr.Textbox(label="Message", placeholder="What do you want to brew?")
│   │   ├── gr.Button("Send")
│   │   └── gr.Accordion("Tool calls", open=False)
│   │       └── gr.Markdown (tool_calls_md — appended each turn)
│   └── gr.Column(scale=4) — Recipe + notes panel
│       ├── gr.JSON(label="Live Recipe State")
│       ├── gr.Button("Refresh Recipe")
│       └── gr.Accordion("Brew Notes", open=False)
│           └── gr.Markdown (brew_notes_md — reads brew_notes/{id}.md after each turn)
├── gr.State(value=[])      # history — list of {"role", "content"} dicts
├── gr.State(value=None)    # session_id — set on first send, stable for the page session
```

**Why Markdown for tool calls instead of Dataframe**: Dataframe requires fixed column shapes each yield. Markdown accumulated as a string is simpler to update incrementally.

**Brew notes panel** (new vs. original plan): FilesystemBackend lands files in `brew_notes/` on disk. After each response, reading the file and surfacing it in the UI makes context offloading (principle #2) visible. This is Phase 4 work, not Phase 5, because FilesystemBackend is already in scope here.

### 4c. SSE consumption — streaming generator

The generator yields 5 values per tick: `history, session_id, tool_calls_md, recipe_update, notes_update`. Outputs list in `.click()` must match this order exactly.

```python
import os
import uuid
import json
from pathlib import Path
import httpx

API_BASE = os.getenv("MCP_BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("LOCAL_API_TOKEN", "test-token")

async def send_message(message, recipe_id, history, session_id):
    if not session_id:
        session_id = str(uuid.uuid4())
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    tool_lines: list[str] = []

    async with httpx.AsyncClient(timeout=180) as client:
        async with client.stream(
            "POST", f"{API_BASE}/chat",
            json={"message": message, "recipe_id": recipe_id, "session_id": session_id},
            headers={"Authorization": f"Bearer {TOKEN}"},
        ) as resp:
            event_type = None
            async for line in resp.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data = line[6:]
                    if event_type == "token":
                        history[-1]["content"] += data
                        yield history, session_id, "\n".join(tool_lines), gr.update(), gr.update()
                    elif event_type == "tool_call":
                        tc = json.loads(data)
                        tool_lines.append(f"**{tc['name']}** — `{json.dumps(tc.get('input',{}))}`")
                        yield history, session_id, "\n".join(tool_lines), gr.update(), gr.update()
                    elif event_type == "error":
                        history[-1]["content"] = f"⚠️ {data}"
                        yield history, session_id, "\n".join(tool_lines), gr.update(), gr.update()
                    elif event_type == "done":
                        break

    recipe_data = _fetch_recipe(recipe_id)
    notes_md = _read_brew_notes(recipe_id)
    yield history, session_id, "\n".join(tool_lines), gr.update(value=recipe_data), gr.update(value=notes_md)
```

### 4d. Helpers — recipe fetch and brew notes read

```python
def _fetch_recipe(recipe_id: str) -> dict | None:
    if not recipe_id:
        return None
    try:
        r = httpx.get(
            f"{API_BASE}/recipe/{recipe_id}",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None

def _read_brew_notes(recipe_id: str) -> str:
    path = Path("brew_notes") / f"{recipe_id}.md"
    return path.read_text() if path.exists() else "*No brew notes yet.*"
```

### 4e. Event wiring

```python
with gr.Blocks(title="BrewAgent") as demo:
    # ... component definitions ...
    history_state = gr.State([])
    session_state = gr.State(None)

    send_btn.click(
        fn=send_message,
        inputs=[msg_box, recipe_id_box, history_state, session_state],
        outputs=[chatbot, session_state, tool_calls_md, recipe_json, notes_md],
    )
    msg_box.submit(
        fn=send_message,
        inputs=[msg_box, recipe_id_box, history_state, session_state],
        outputs=[chatbot, session_state, tool_calls_md, recipe_json, notes_md],
    )
    refresh_btn.click(
        fn=lambda rid: (gr.update(value=_fetch_recipe(rid)), gr.update(value=_read_brew_notes(rid))),
        inputs=[recipe_id_box],
        outputs=[recipe_json, notes_md],
    )
```

Note: `msg_box.submit` fires on Enter, `send_btn.click` fires on button press — both wire the same function. Clear the message box after submit by adding it to outputs with `gr.update(value="")`.

### 4f. FilesystemBackend — `src/agents/orchestrator.py`

**Confirmed import path (verified):** `from deepagents.backends import FilesystemBackend` — NOT `from deepagents import FilesystemBackend` (that fails in 0.5.7).

```python
from pathlib import Path
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model=get_model(),
    tools=tools,
    system_prompt=SYSTEM_PROMPT.format(recipe_id=recipe_id),
    checkpointer=_checkpointer,
    subagents=[STYLE_CONSULTANT, INGREDIENT_ANALYST, SENSORY_PROFILER],
    skills=["data/skills/"],
    backend=FilesystemBackend(root_dir=Path(".")),
)
```

`MemorySaver` still handles conversation history. `FilesystemBackend` only controls where `write_file`/`read_file` tool calls land. With this, `brew_notes/{recipe_id}.md` actually appears on disk.

### 4g. Launch — `scripts/02_start_ui.sh`

```bash
#!/usr/bin/env bash
# Requires FastAPI running on port 8000 first (scripts/00_start.sh)
uv run python -m src.ui.app
```

`src/ui/app.py` entry point:
```python
if __name__ == "__main__":
    demo.launch(server_port=7860)
```

Run with `python -m src.ui.app` — the `-m` flag requires `src/ui/__init__.py` to exist (empty file).

### 4h. Tests

Gradio generator wiring is integration territory — no unit tests for it. Test only the pure helpers:

`tests/test_ui/test_helpers.py`:
- `_fetch_recipe` with `httpx.MockTransport`:
  - 200 → returns parsed dict
  - 404 → returns `None`
  - `httpx.RequestError` → returns `None`
  - empty recipe_id → returns `None` without making a request
- `_read_brew_notes`:
  - file exists → returns file content
  - file missing → returns `"*No brew notes yet.*"`

### 4i. Critical files

| File | Action |
|---|---|
| `src/ui/__init__.py` | Create (empty) |
| `src/ui/app.py` | Create (Gradio Blocks app) |
| `src/agents/orchestrator.py` | Update (add `FilesystemBackend` from `deepagents.backends`) |
| `scripts/02_start_ui.sh` | Create |
| `tests/test_ui/__init__.py` | Create (empty) |
| `tests/test_ui/test_helpers.py` | Create (`_fetch_recipe` + `_read_brew_notes` tests) |

---

## Phase 4.5 — Langfuse Observability

**Goal:** Trace every agent run — tokens, tool calls, latency, cost. Graceful no-op when disabled.

### Implementation

Add dep: `langfuse` to `pyproject.toml`.

`src/observability/langfuse.py` — singleton pattern (same as fcx-atlantis):

```python
from langfuse.callback import CallbackHandler

class LangfuseManager:
    _handler: CallbackHandler | None = None

    @classmethod
    def get_handler(cls) -> CallbackHandler | None:
        if not settings.LANGFUSE_ENABLED:
            return None
        if cls._handler is None:
            cls._handler = CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
        return cls._handler
```

In `src/endpoints/chat.py`, add handler to `config`:
```python
from src.observability.langfuse import LangfuseManager
config: RunnableConfig = {
    "configurable": {"thread_id": body["session_id"]},
    "callbacks": [h] if (h := LangfuseManager.get_handler()) else [],
}
```

Config already has `LANGFUSE_ENABLED`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — no changes to `config.py`.

### Critical files

| File | Action |
|---|---|
| `src/observability/__init__.py` | Create |
| `src/observability/langfuse.py` | Create (LangfuseManager singleton) |
| `src/endpoints/chat.py` | Update (add callbacks to RunnableConfig) |
| `pyproject.toml` | Add `langfuse>=2.0.0` |

---

## Phase 4 — Gradio UI ✅ COMPLETE

**Delivered:**
- `src/ui/__init__.py`, `src/ui/app.py` — Gradio 6 Blocks app: chat panel (left) + live recipe JSON + brew notes accordion (right); 5-output async SSE streaming generator; `history_state` in outputs so conversation persists across turns; `recipe_id_box` auto-populated from auto-generated UUID
- `src/agents/orchestrator.py` — `FilesystemBackend(root_dir=abs_path, virtual_mode=False)` so `write_file` lands on disk; system prompt adds hop `use` validation and mandatory post-mutation `get_recipe_by_id` verification loop
- `src/resources/recipe.py` — `create_recipe` honors provided `id` field so UI-generated UUID matches DB record
- `src/service/recipe.py` — IBU formula fix: `alpha_pct` used as whole number (not divided by 100); filter reverted to `!= "boil"` so invalid `use` values get 0 IBU safely
- `data/skills/*/SKILL.md` — YAML frontmatter added to all 4 skill files (required by deepagents skills loader)
- `scripts/02_start_ui.sh`, `tests/test_ui/test_helpers.py` — 7 tests covering async `_fetch_recipe` and `_read_brew_notes`

**Key corrections discovered during Phase 4 testing:**
- `virtual_mode=True` keeps files in agent state (in-memory) — must be `False` for brew notes to hit disk
- `_fetch_recipe` was a blocking sync call inside an async generator — converted to `async def` with `httpx.AsyncClient`
- `_read_brew_notes` used `Path("brew_notes")` relative to CWD — anchored to `_REPO_ROOT = Path(__file__).resolve().parent.parent.parent`
- `history_state` missing from `_outputs` — conversation reset to `[]` on every turn
- Recipe ID mismatch: UI-generated UUID ≠ DB UUID — fixed by honoring `id` in `create_recipe` + system prompt instruction
- Agent invented grain quantities from style percentages without calculating OG — fixed by mandatory post-creation verification loop in system prompt
- SKILL.md files silently skipped: deepagents requires YAML frontmatter with `name` + `description`

**Known limitation — single-user filesystem:**
Brew notes land at `brew_notes/{recipe_id}.md` on the server's filesystem. UUIDs prevent collision between recipes but there is no per-user namespacing and no cleanup. Safe for single-user local use; revisit when auth is added.

---

## Phase 4.5 — Langfuse Observability ⏭ SKIPPED

Deferred indefinitely. No Langfuse for now.

---

## Phase 5 — Persistent Sessions ✅ COMPLETE

**Delivered:**
- `pyproject.toml` + `uv.lock`: `langgraph-checkpoint-sqlite>=3.0.3`
- `src/config.py`: `CHECKPOINT_DB_PATH`, `CHECKPOINT_MAX_THREADS`
- `src/agents/orchestrator.py`: `set_checkpointer()` injection, `prune_old_checkpoints()` (uses `adelete_thread` public API for both tables), `BaseCheckpointSaver` type, `memory=["brew_notes/user_preferences.md"]` (conditional on file existence), `virtual_mode=True` on `FilesystemBackend` (sandboxes agent writes within repo root)
- `src/main.py`: `AsyncSqliteSaver.from_conn_string` in lifespan, `set_checkpointer`, pruning call wrapped in `try/except` so a failure degrades gracefully
- `src/ui/app.py`: `gr.BrowserState(None)` — session UUID persists to `localStorage`, survives page refresh
- `tests/test_agents/test_orchestrator.py`: `test_set_checkpointer_swaps_module_singleton`
- `src/endpoints/chat.py`: `stream_ok` flag + `isinstance(exc, BaseExceptionGroup)` guard — suppresses LangGraph/MCP teardown noise, surfaces real errors only
- `.gitignore`: `brew_notes/`

**Key corrections discovered during Phase 5:**
- `async with checkpointer.conn` closes the shared connection — use `async with checkpointer.conn.cursor() as cur` instead
- `checkpoints` table doesn't exist on first startup — call `await checkpointer.setup()` before any SQL
- Custom SQL leaves orphaned `writes` rows — use `adelete_thread()` public API which deletes both tables
- Pruning failure must not crash startup — wrapped in `try/except logger.warning`
- `user_preferences.md` doesn't exist on first run — conditional `_PREFS_PATH.exists()` check
- `ExceptionGroup` from LangGraph checkpoint writes propagates through `astream_events` with `stream_ok=False` — must suppress by type, not just by flag
- Agent invented `/tmp/brew_notes/...` path — `virtual_mode=True` sandboxes writes within `root_dir`; system prompt made explicit

**Goal:** Conversation history survives server restarts. `session_id` persists in the browser so users reconnect to their thread after a page refresh. User preferences accumulate across sessions via the `memory=` param.

### Context

Currently `MemorySaver` is a module-level in-process singleton. It holds conversation history and agent state (todo lists, etc.) only while the server process is alive. A server restart wipes all sessions. Additionally, `session_id` in the UI is a `gr.State` that resets on page refresh — the user loses their thread even if the server is still running.

**`AsyncSqliteSaver` is not currently installed.** It requires the `langgraph-checkpoint-sqlite` package (separate from `langgraph`). Note: `aiosqlite` is already installed as a dep.

**`gr.BrowserState` is available** in Gradio 6.14.0 — can persist `session_id` to `localStorage` so page refreshes reconnect to the existing thread.

### 5a. New dependency

Add to `pyproject.toml`:
```toml
"langgraph-checkpoint-sqlite>=2.0.0",
```

### 5b. Two databases — why separate

| DB | File | What's in it | Who reads/writes it |
|---|---|---|---|
| `brew.db` | Recipe data | `recipes` table — fermentables, hops, yeast, calculated stats | FastAPI CRUD endpoints + MCP tools |
| `brew_checkpoints.db` | Conversation state | LangGraph checkpoint tables — full message history, todo list state, agent state per `thread_id` | LangGraph `AsyncSqliteSaver` only |

They **must** be separate: different schemas, different access patterns (SQL CRUD vs LangGraph checkpoint API), and different lifecycles — recipes are permanent, checkpoints can be pruned.

### 5c. Config — `src/config.py`

```python
CHECKPOINT_DB_PATH: str = "brew_checkpoints.db"
CHECKPOINT_MAX_THREADS: int = 500   # prune oldest threads above this count
```

### 5d. Checkpointer lifecycle — module-level + lifespan

`AsyncSqliteSaver` must stay open for the server's lifetime. Initialize in `main.py` lifespan and inject into orchestrator via a setter:

```python
# src/agents/orchestrator.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

# Falls back to MemorySaver so tests don't need a real DB
_checkpointer: BaseCheckpointSaver = MemorySaver()

def set_checkpointer(checkpointer: BaseCheckpointSaver) -> None:
    global _checkpointer
    _checkpointer = checkpointer
```

```python
# src/main.py  lifespan
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.agents.orchestrator import set_checkpointer

@asynccontextmanager
async def lifespan(app):
    await init_db(settings.DB_PATH)
    os.makedirs("brew_notes", exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as cp:
        set_checkpointer(cp)
        async with mcp_app.router.lifespan_context(mcp_app):
            yield
```

The `recipe_agent_context` already passes `_checkpointer` to `create_deep_agent` — no change needed there.

### 5e. Checkpoint memory management

`AsyncSqliteSaver` stores every turn of every conversation indefinitely. Left unchecked the DB grows without bound. Add a lightweight pruning step in lifespan — after the checkpointer is opened, delete threads that haven't been touched in more than 30 days:

```python
# src/agents/orchestrator.py
async def prune_old_checkpoints(
    checkpointer: AsyncSqliteSaver, max_threads: int
) -> None:
    """Delete oldest threads when count exceeds max_threads."""
    async with checkpointer.conn as conn:
        await conn.execute(
            """
            DELETE FROM checkpoints
            WHERE thread_id IN (
                SELECT thread_id FROM checkpoints
                GROUP BY thread_id
                ORDER BY MAX(checkpoint_id) ASC
                LIMIT MAX(0, (SELECT COUNT(DISTINCT thread_id) FROM checkpoints) - ?)
            )
            """,
            (max_threads,),
        )
        await conn.commit()
```

Called once at startup in `main.py` lifespan after `set_checkpointer`. The exact LangGraph checkpoint schema may differ — adjust table/column names after inspecting the actual schema on first run.

### 5f. User preferences via `memory=`

Once `FilesystemBackend` is confirmed working (Phase 4), enable the `memory=` param:

```python
agent = create_deep_agent(
    ...
    checkpointer=_checkpointer,
    memory=["brew_notes/user_preferences.md"],
)
```

The agent can `write_file("brew_notes/user_preferences.md", "User prefers 20L batches, English styles")`. On the next session deepagents injects this file into the system prompt automatically. The file lives on disk (FilesystemBackend), so it survives restarts.

### 5g. Browser session persistence — `src/ui/app.py`

Replace `gr.State(None)` for `session_state` with `gr.BrowserState(None)`:

```python
# Before:
session_state: gr.State = gr.State(None)

# After:
session_state = gr.BrowserState(None)
```

`gr.BrowserState` serializes the value to `localStorage`. On page refresh Gradio rehydrates it — the existing `session_id` UUID is restored and the next `/chat` call reuses the same LangGraph `thread_id`, reconnecting to the persisted conversation. No other changes needed; the rest of the send_message flow is unchanged.

**Note:** `history_state` stays as `gr.State` (not BrowserState). The chat display history is rebuilt from the server-side thread on reconnect — storing full message history in localStorage would hit size limits.

### 5h. Tests

- `tests/test_agents/test_orchestrator.py` — add test that `set_checkpointer` swaps the module-level instance; existing compile tests continue to use the default `MemorySaver` fallback (no DB needed)
- `src/main.py` lifespan test — mock `AsyncSqliteSaver.from_conn_string` and verify `set_checkpointer` is called

### 5i. Future work (not Phase 5)

- **Per-user brew notes namespacing**: currently all brew notes land in `brew_notes/{recipe_id}.md` on the server filesystem with no user isolation. When user auth is added, migrate to `brew_notes/{user_id}/{recipe_id}.md` and add cleanup on account deletion.
- **Brew notes storage backend**: for multi-user deployments, move brew notes from local filesystem to object storage (S3/GCS) so horizontal scaling works.

### 5j. Critical files

| File | Action |
|---|---|
| `pyproject.toml` | Add `langgraph-checkpoint-sqlite>=2.0.0` |
| `src/config.py` | Add `CHECKPOINT_DB_PATH` |
| `src/agents/orchestrator.py` | Replace `MemorySaver()` singleton with `BaseCheckpointSaver` + `set_checkpointer()`; add `memory=` param |
| `src/main.py` | Init `AsyncSqliteSaver` in lifespan, call `set_checkpointer` |
| `src/ui/app.py` | `session_state = gr.BrowserState(None)` |
| `tests/test_agents/test_orchestrator.py` | Add `set_checkpointer` swap test |

---

## Phase 6 — Human-in-the-Loop (text-only, prompt-driven) ✅ COMPLETE

**Goal:** Agent describes planned recipe changes and asks for user confirmation before executing them. User approves or gives feedback by typing in the chat — no buttons, no separate resume endpoint. Pure conversational HITL enforced via the system prompt.

**Design decision:** Dropped `interrupt_on` / `Command(resume=...)` / button panel in favor of asking the agent to pause in text. Simpler UX, fewer moving parts, no LangGraph interrupt state to manage across request boundaries.

**Delivered:**
- `src/resources/recipe.py` — `ensure_recipe` (`INSERT OR IGNORE` with full valid placeholder); pre-called on every `/chat` so agent always PATCHes, never POSTs
- `src/endpoints/chat.py` — removed `resume_chat`, interrupt detection, `_build_interrupt_payload`; added `ensure_recipe` call; `ensure_recipe` mocked in all chat tests
- `src/models/chat.py` — removed `ApproveRequest` (only `ChatRequest` remains)
- `src/agents/orchestrator.py` — removed `interrupt_on` + `InterruptOnConfig` import; fixed MCP tool names (`patch_recipe_recipe`, `get_recipe_by_id_recipe`); system prompt: recipe is pre-created, agent must describe changes and wait for user agreement before patching
- `src/ui/app.py` — removed interrupt panel, `_resume`, `_format_interrupt`; `_YieldTuple` back to 8 items
- `tests/test_recipe_resource.py` — 3 new tests for `ensure_recipe`: creates placeholder, idempotent no-op, correct placeholder fields
- 67 tests pass

**Key corrections discovered:**
- FastMCP actual tool names are `patch_recipe_recipe` and `get_recipe_by_id_recipe` — NOT the verbose `__recipe_id__patch` / `__recipe_id__get` forms that were in the original plan
- `ensure_recipe` placeholder must include all required `Recipe` fields (empty lists, default yeast) — a partial `{"id": recipe_id}` causes `ResponseValidationError` in the list endpoint

**Future (Phase 8b React UI):** Replace text-only confirmation with a structured approve/reject panel similar to Claude Code's interrupt UX (Yes / Yes with changes / No + reason). Gradio makes this awkward; React makes it straightforward.

---

## Phase 7a — Richer Static Skills

**Goal:** Expand the hand-curated SKILL.md files with more complete domain coverage. No architecture change — pure content work.

**Why before 7b:** Cheap, immediate quality gain for the agent. Skills are read at agent-creation time so improvements are felt instantly without any infra changes.

### Scope

| Skill file | Current state | Additions |
|---|---|---|
| `bjcp-styles` | 37 styles, OG/IBU/SRM/ABV ranges | Water profile targets, carbonation, serving temp, common flaws per style |
| `hop-pairing` | 40 hops, flavor categories | Cryo/T90 equivalents, substitution ratios, biotransformation notes |
| `yeast-profiles` | 22 strains | Flocculation, alcohol tolerance, co-fermentation notes, pressure-fermenting guidance |
| `ingredient-substitutions` | Malt/hop/yeast tables | Regional availability notes, extract equivalents, adjunct ratios |
| `fermentation-science` | *(new)* | Mash temp → body/fermentability, yeast pitching rates, dry hop timing, common off-flavour diagnostics |
| `water-chemistry` | *(new)* | Ca/Mg/SO4/Cl targets per style family, simple salt addition table, mash pH targets |

### Critical files

| File | Action |
|---|---|
| `data/skills/bjcp-styles/SKILL.md` | Expand |
| `data/skills/hop-pairing/SKILL.md` | Expand |
| `data/skills/yeast-profiles/SKILL.md` | Expand |
| `data/skills/ingredient-substitutions/SKILL.md` | Expand |
| `data/skills/fermentation-science/SKILL.md` | Create |
| `data/skills/water-chemistry/SKILL.md` | Create |

---

## Phase 7b — Hybrid Retrieval over Brewing PDFs

**Goal:** Replace the fixed-size SKILL.md files with on-demand retrieval over the full BJCP guidelines PDF and an ingredients reference. The agent calls a `search_brewing_knowledge(query)` tool instead of relying on pre-loaded text.

**Why after 8a:** Independent infrastructure work, can run in parallel with UI phases. Doing it after 8a means the recipe selection UX is already stable so manual testing is easier.

### Architecture

```
data/pdfs/bjcp-guidelines.pdf          ← source documents
data/pdfs/ingredients-reference.pdf

scripts/03_ingest_knowledge.sh         ← one-time ingestion pipeline
  uv run python -m src.knowledge.ingest

src/knowledge/ingest.py                ← PDF → chunks → embeddings → vector store
src/knowledge/retriever.py             ← hybrid search: BM25 + vector (Chroma)
src/endpoints/knowledge.py             ← GET /knowledge/search?q=... (MCP tool)
```

**Stack choices:**
- Vector store: **Chroma** (local, no infra) for Phase 7b; swap to Qdrant for production
- Embeddings: `langchain-ollama` (`nomic-embed-text`) for local; `langchain-openai` for cloud
- BM25: `rank_bm25` Python package
- Chunking: 512-token chunks with 64-token overlap, per-document metadata (source, section)

### Agent integration

Replace `skills=["data/skills/"]` on `create_deep_agent` with a `search_brewing_knowledge` MCP tool exposed via `GET /knowledge/search`. The orchestrator system prompt instructs the agent to call it for style lookups, ingredient questions, and off-flavour diagnosis instead of relying on pre-loaded text.

Existing SKILL.md files stay as a fallback — the agent can use both.

### Critical files

| File | Action |
|---|---|
| `pyproject.toml` | Add `chromadb`, `rank-bm25`, `langchain-chroma` |
| `src/knowledge/__init__.py` | Create |
| `src/knowledge/ingest.py` | Create — PDF chunking + embedding pipeline |
| `src/knowledge/retriever.py` | Create — hybrid BM25 + vector search |
| `src/endpoints/knowledge.py` | Create — `GET /knowledge/search` route |
| `src/main.py` | Add knowledge router |
| `scripts/03_ingest_knowledge.sh` | Create — one-time ingestion script |
| `src/agents/orchestrator.py` | Add `search_brewing_knowledge` to system prompt tool list |

---

## Phase 8a — Recipe List + Selection (still Gradio)

**Goal:** Replace the manual UUID text box with a recipe selector. User sees their existing recipes by name on load and can switch between them or start a new one. High UX impact, feasible within Gradio.

**Why Gradio still works here:** Recipe list is a dropdown + refresh button — no editable tables needed yet.

### Changes

- `GET /recipes` returns `id + name`; already implemented.
- Replace `recipe_id_box` (Textbox) with a `gr.Dropdown` populated from `GET /recipes` on load and after each agent turn (new recipe auto-added to the list).
- "New recipe" option at the top generates a fresh UUID and clears the chat.
- `refresh_btn` also refreshes the dropdown.

### Critical files

| File | Action |
|---|---|
| `src/ui/app.py` | Replace `recipe_id_box` Textbox with `gr.Dropdown`; add load event to populate it |

---

## Phase 8b — React Frontend (read-only)

**Goal:** Replace Gradio with a proper React app. FastAPI backend unchanged. First milestone: display-only — recipe card with formatted tables, chat panel, brew notes. No editing yet.

**Stack:** Vite + React + TypeScript. No heavy UI framework — plain CSS or Tailwind. `frontend/` directory at repo root, served by FastAPI as static files in production or via Vite dev server in development.

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  BrewAgent                          [Recipe selector ▼]  │
├──────────────────────┬───────────────────────────────────┤
│  Chat                │  Recipe Card                      │
│                      │  ┌─ Fermentables ──────────────┐  │
│  [messages]          │  │ Pale Malt  4.0 kg  5 EBC    │  │
│                      │  │ Crystal    0.5 kg  120 EBC  │  │
│                      │  └──────────────────────────────┘  │
│                      │  ┌─ Hops ──────────────────────┐  │
│  [tool calls]        │  │ Cascade  30g  60min  boil   │  │
│                      │  └──────────────────────────────┘  │
│  [message input]     │  ┌─ Stats ─────────────────────┐  │
│  [Send]              │  │ OG 1.062  IBU 42  ABV 6.1%  │  │
│                      │  └──────────────────────────────┘  │
│                      │  ┌─ Brew Notes ────────────────┐  │
│                      │  │ (markdown render)            │  │
│                      │  └──────────────────────────────┘  │
└──────────────────────┴───────────────────────────────────┘
```

### Critical files

| File | Action |
|---|---|
| `frontend/` | Create — Vite + React + TypeScript project |
| `frontend/src/components/ChatPanel.tsx` | Create |
| `frontend/src/components/RecipeCard.tsx` | Create |
| `frontend/src/api/client.ts` | Create — typed wrappers for `/chat` SSE and `/recipe/{id}` |
| `src/main.py` | Serve `frontend/dist/` as static files in production |
| `scripts/03_start_frontend.sh` | Create — `npm run dev` |

---

## Phase 8c — Editable Recipe Fields

**Goal:** Every field in the recipe card becomes editable. Changing a value calls `PATCH /recipe/{id}` and recalculates stats inline. This is the core Brewfather-like loop: the agent and the form are both first-class ways to mutate the same recipe.

**Key interactions:**
- Fermentables table: add/remove rows, edit amount/ppg/color inline — `PATCH` on blur
- Hops table: same pattern, plus `use` dropdown (boil/whirlpool/dry-hop)
- Yeast: single editable card
- Stats bar: recalculates after every patch (calls `GET /recipe/{id}`)
- Style selector: dropdown from `GET /styles` (new endpoint from `src/data/styles.json`)

### New endpoint needed

`GET /styles` — returns the list of BJCP styles from `src/data/styles.json`. Used to populate the style selector dropdown.

### Critical files

| File | Action |
|---|---|
| `frontend/src/components/FermentablesTable.tsx` | Create — editable rows |
| `frontend/src/components/HopsTable.tsx` | Create — editable rows + use dropdown |
| `frontend/src/components/StatsBar.tsx` | Create — live recalculation |
| `src/endpoints/recipe.py` | Add `GET /styles` |
| `src/models/recipe.py` | Add `Style` TypedDict if needed |

---

## Phase 8d — Polish

**Goal:** Quality-of-life features once the core loop works.

- Brew day mode: step-by-step view (mash, sparge, boil, fermentation timers)
- Print / export view: clean recipe sheet, BeerXML export (`GET /recipe/{id}/beerxml`)
- Mobile layout: responsive CSS, chat collapses to a tab
- Recipe duplication: `POST /recipe/{id}/clone`
- Delete recipe: `DELETE /recipe/{id}` with HITL confirmation (Phase 6 pattern)

---

## Recommended Order

```
Phase 6  (HITL)              ← medium complexity, self-contained
    ↓
Phase 7a (richer skills)     ← content-only, fast
    ↓
Phase 8a (recipe dropdown)   ← still Gradio, single file change
    ↓
Phase 7b (PDF retrieval)     ← can run in parallel with 8b
Phase 8b (React read-only)   ←
    ↓
Phase 8c (editable fields)
    ↓
Phase 8d (polish)
```

**Why this order:**
- 6 before 7a — HITL makes the agent safer before we invest more in its domain knowledge
- 7a before 8a — better skills improve every recipe session; no frontend work needed
- 8a before 8b — ships a UX improvement in Gradio while the React rewrite is planned
- 7b and 8b in parallel — independent work streams; 7b is backend, 8b is frontend
- 8c requires 8b to exist first

---

## Critical Files

| File | Status | Action |
|---|---|---|
| `pyproject.toml` | ✅ done | — |
| `src/config.py` | ✅ done | — |
| `src/agents/base.py` | ✅ done | — |
| `src/middleware.py` | ✅ unchanged | Auth forwarded via MCP client headers |
| `src/main.py` | ✅ done (Phase 1) | Phase 2: add `brew_notes` mkdir to lifespan; add chat router |
| `src/models/recipe.py` | ✅ done | — |
| `src/models/__init__.py` | ✅ done | — |
| `src/data/fermentables.json` | ✅ done | — |
| `src/data/hops.json` | ✅ done | — |
| `src/data/yeasts.json` | ✅ done | — |
| `src/data/styles.json` | ✅ done | — |
| `src/service/recipe.py` | ✅ done | — |
| `src/service/__init__.py` | ✅ done | — |
| `src/resources/recipe.py` | ✅ done | — |
| `src/resources/__init__.py` | ✅ done | — |
| `src/endpoints/recipe.py` | ✅ done | — |
| `src/models/chat.py` | ✅ done (Phase 2) | — |
| `src/endpoints/chat.py` | ✅ done (Phase 2) | Phase 4.5: add Langfuse callbacks; Phase 6: add interrupt event + resume endpoints |
| `src/agents/orchestrator.py` | ✅ done (Phase 2+3) | Phase 4: FilesystemBackend; Phase 5: AsyncSqliteSaver+memory; Phase 6: interrupt_on |
| `tests/test_agents/test_orchestrator.py` | ✅ done (Phase 2) | — |
| `tests/test_chat_endpoint.py` | ✅ done (Phase 2) | — |
| `data/skills/bjcp-styles/SKILL.md` | ✅ done (Phase 3) | — |
| `data/skills/hop-pairing/SKILL.md` | ✅ done (Phase 3) | — |
| `data/skills/yeast-profiles/SKILL.md` | ✅ done (Phase 3) | — |
| `data/skills/ingredient-substitutions/SKILL.md` | ✅ done (Phase 3) | — |
| `src/agents/subagents.py` | ✅ done (Phase 3) | — |
| `tests/test_agents/test_subagents.py` | ✅ done (Phase 3) | — |
| `src/ui/__init__.py` | ✅ done (Phase 4) | — |
| `src/ui/app.py` | ✅ done (Phase 4) | Phase 5: `gr.BrowserState` for session_state |
| `scripts/02_start_ui.sh` | ✅ done (Phase 4) | — |
| `tests/test_ui/__init__.py` | ✅ done (Phase 4) | — |
| `tests/test_ui/test_helpers.py` | ✅ done (Phase 4) | — |
| `pyproject.toml` | ✅ done (Phase 5) | Phase 7b: add `chromadb`, `rank-bm25`, `langchain-chroma` |
| `src/config.py` | ✅ done (Phase 5) | — |
| `src/agents/orchestrator.py` | ✅ done (Phase 6) | — |
| `src/main.py` | ✅ done (Phase 5) | Phase 7b: add knowledge router |
| `src/endpoints/chat.py` | ✅ done (Phase 6) | — |
| `src/ui/app.py` | ✅ done (Phase 6) | Phase 8a: recipe dropdown |
| `src/resources/recipe.py` | ✅ done (Phase 6) | — |
| `src/models/chat.py` | ✅ done (Phase 6) | — |
| `tests/test_agents/test_orchestrator.py` | ✅ done (Phase 5) | — |
| `tests/test_chat_endpoint.py` | ✅ done (Phase 6) | — |
| `tests/test_recipe_resource.py` | ✅ done (Phase 6) | — |
| `data/skills/*/SKILL.md` | Phase 7a | Expand all; add fermentation-science + water-chemistry |
| `src/knowledge/` | Phase 7b | New — ingest + retriever + endpoint |
| `src/endpoints/knowledge.py` | Phase 7b | New — `GET /knowledge/search` |
| `frontend/` | Phase 8b | New — Vite + React + TypeScript |
| `src/endpoints/recipe.py` | Phase 8c | Add `GET /styles` |

---

## Verification

1. **Phase 0:** `uv run pytest tests/test_agents/test_base.py -v` — passes ✅
2. **Phase 1:** `uv run pytest tests/test_recipe_service.py tests/test_recipe_endpoints.py -v` — 29 tests pass ✅
3. **Phase 1 MCP check:** Start server (`bash scripts/00_start.sh`), hit `GET /mcp` — recipe tools appear in MCP manifest
4. **Phase 2 compile check:** `uv run pytest tests/test_agents/test_orchestrator.py -v` — orchestrator graph compiles with mocked MCP
5. **Phase 2 SSE check:** `uv run pytest tests/test_chat_endpoint.py -v` — streaming response has correct content-type
6. **Phase 2 manual test:** Start server, call `POST /chat` with `{"recipe_id": "...", "message": "I want to brew an American IPA, 20L batch", "session_id": "test"}` — SSE stream shows `tool_call` event for `write_todos` before any recipe mutation
7. **Phase 3 sub-agent check:** `uv run pytest tests/test_agents/test_subagents.py tests/test_recipe_endpoints.py -v` — 16 tests pass ✅
8. **Phase 3 manual test:** `curl .../recipe/{id}/profile` — returns `{aroma, flavor, mouthfeel, appearance}` JSON in ~60s ✅
9. **Coverage:** `make cov` must stay ≥70%
10. **Lint/types:** `make check` must pass
11. **Phase 4 FilesystemBackend check:** after chat turn, verify `brew_notes/{recipe_id}.md` exists on disk ✅
12. **Phase 4 UI check:** start FastAPI + Gradio, open `http://localhost:7860`, send a message, confirm tokens stream token-by-token in the chatbot and recipe JSON updates after response completes ✅
13. **Phase 5 persistence check:** restart server mid-conversation; reload page; confirm session_id is restored from localStorage and chat resumes with full history ✅
14. **Phase 5 user preferences check:** ask agent to remember a preference (e.g. "I always brew 20L batches"); restart server; start new chat and confirm the preference appears in the agent's context without re-stating it ✅
15. **Phase 6 HITL check:** send a recipe mutation request; confirm agent describes planned changes in text before patching; reply with feedback; agent revises and re-asks ✅
16. **Phase 7a skills check:** ask agent about water profile for a Czech Pils — confirm it cites Ca/SO4/Cl targets from the new skill file
17. **Phase 7b retrieval check:** run `scripts/03_ingest_knowledge.sh`; call `GET /knowledge/search?q=Citra+hop+aroma`; confirm chunks returned from the PDF
18. **Phase 8a dropdown check:** open UI; confirm recipe dropdown is populated from `GET /recipes`; switching recipe updates the recipe card
19. **Phase 8c edit check:** change a fermentable amount in the UI; confirm `PATCH /recipe/{id}` fires and stats recalculate inline
