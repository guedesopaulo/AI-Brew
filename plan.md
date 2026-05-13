# BrewAgent — Deep Agents Exploration via Beer Recipe App

## Goal

Use this repo as a laboratory to explore the **deepagents harness** (planning, context offloading, sub-agent delegation, prompt design) while building a practical domain app: a beer recipe assistant similar to Brewfather / BeerSmith, but with chat + AI agents.

The beer domain is intentionally rich: calculations are deterministic (OG, FG, IBU, SRM), ingredient knowledge is deep (hundreds of malts, hops, yeasts), and sensory prediction is fuzzy — a perfect playground for agents that plan, delegate, and reason.

Here is a good example on deepagents usage: https://github.com/langchain-ai/deepagents/tree/main/examples/nvidia_deep_agent/src

We can incert MCP sercer for beer: https://github.com/CharlRitter/brewsource-mcp (did not test it)
---

## Deep Agents Principles — Concrete Mapping

| Principle | How it shows up here |
|---|---|
| **Planning-first** | Orchestrator writes a `recipe_plan.md` before touching any parameter. The user can review it before the agent acts (human-in-the-loop). |
| **Context offloading** | The live recipe is stored as a structured JSON artifact (`recipe.json`), not stuffed into the prompt. Agents read/write it via file tools. |
| **Task delegation** | Orchestrator spawns specialist sub-agents: Style Consultant, Ingredient Analyst, Sensory Profiler. Each gets only the slice of context it needs. |
| **Prompt design** | Each agent and sub-agent has a tightly scoped system prompt. Quality of coordination depends directly on prompt clarity. |

---

## Architecture

```
User (chat / REST)
        │
        ▼
┌──────────────────────────────────────────────┐
│  FastAPI  (src/)                             │
│  ├─ POST /chat        ← streaming SSE        │
│  ├─ GET/POST /recipe  ← CRUD                 │
│  ├─ GET /recipe/{id}/profile  ← sensory      │
│  └─ /mcp              ← FastMCP mount        │
└──────────────┬───────────────────────────────┘
               │  MCP tools (via langchain-mcp-adapters)
               ▼
┌─────────────────────────────────────────────────────┐
│  Recipe Orchestrator Agent  (deepagents)            │
│  Model: any (openai / anthropic / gemini / ollama)  │
│                                                     │
│  Built-in tools:  write_todos, read_file,           │
│                   write_file, edit_file             │
│  MCP tools:       get_recipe, update_recipe,        │
│                   calculate_stats, list_styles      │
│                                                     │
│  Spawns sub-agents via `task` tool:                 │
│   ├─ Style Consultant    → suggests style params    │
│   ├─ Ingredient Analyst  → malt/hop/yeast profiles  │
│   └─ Sensory Profiler    → aroma/flavor/body text   │
└─────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  Recipe Service (src/service/recipe.py)             │
│  - Pure calculations: OG, FG, ABV, IBU, SRM         │
│  - Ingredient lookup (JSON ingredient database)     │
└─────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  Storage (src/resources/recipe.py)                  │
│  - SQLite via aiosqlite  (simple, local, no server) │
└─────────────────────────────────────────────────────┘
```

---

## Domain Model (MVP)

```
Recipe
├── id, name, style (string for now)
├── batch_size_liters
├── fermentables: [ {name, amount_kg, color_ebc, ppg} ]
├── hops:         [ {name, amount_g, alpha_pct, time_min, use} ]
├── yeast:        { name, attenuation_pct, min_temp, max_temp }
└── calculated:   { og, fg, abv, ibu, srm }  ← derived, not stored

SensoryProfile  (LLM-generated, cached)
├── aroma: str
├── flavor: str
├── mouthfeel: str
└── appearance: str
```

Ingredient databases ship as static JSON files in `src/data/`:
- `fermentables.json` — ~50 common malts/adjuncts
- `hops.json` — ~40 common hops (alpha range, flavor descriptors)
- `yeasts.json` — ~20 common strains (attenuation, flavor notes)

---

## Phases

### Phase 0 — Foundations (deepagents hello world)
**Goal:** Get deepagents running inside this repo. Understand the tool loop.

- [ ] Add dependencies: `deepagents`, `langchain-mcp-adapters`, `aiosqlite`, `langchain-openai` (or `langchain-anthropic`)
- [ ] Create `src/agents/base.py` — instantiate a bare `create_deep_agent()` with no custom tools
- [ ] Write a smoke test: agent receives "what is an IPA?" and must use `write_todos` to plan its answer
- [ ] Observe the plan-first behavior in LangSmith traces (or stdout)

**deepagents concept explored:** How `write_todos` + the default harness prompt force the model to plan before acting.

---

### Phase 1 — Recipe Domain (REST + calculations)
**Goal:** Build the deterministic core that the agents will later manipulate.

- [ ] `src/models/recipe.py` — TypedDicts for Recipe, Fermentable, Hop, Yeast, CalculatedStats
- [ ] `src/service/recipe.py` — pure calculation functions (no I/O):
  - `calc_og(fermentables, batch_liters) -> float`
  - `calc_ibu_tinseth(hops, og, batch_liters) -> float`
  - `calc_srm_morey(fermentables, batch_liters) -> float`
  - `calc_abv(og, fg) -> float`
- [ ] `src/resources/recipe.py` — aiosqlite CRUD: `create`, `get`, `update`, `list`
- [ ] `src/endpoints/recipe.py` — FastAPI routes:
  - `POST /recipe` — create
  - `GET /recipe/{id}` — read with calculated stats
  - `PATCH /recipe/{id}` — partial update
  - `GET /recipes` — list
- [ ] Unit tests for all calculation functions (pure functions → easy to test)
- [ ] FastMCP auto-exposes these endpoints as MCP tools (no extra work needed)

---

### Phase 2 — Orchestrator Agent + Planning
**Goal:** The agent can take a user's natural-language request and modify a recipe through structured planning.

- [ ] `src/agents/orchestrator.py` — `create_recipe_agent(recipe_id)`:
  - MCP tools loaded via `langchain-mcp-adapters` pointing at `/mcp`
  - System prompt: role as "expert homebrewer assistant", instructions to always plan first, never skip `write_todos`
  - Context offload: agent `read_file("recipe.json")` at start, `write_file` to persist its working notes
- [ ] `POST /chat` endpoint that streams the agent's response via SSE
- [ ] Test scenario: "I want to brew an American IPA, 20L batch" → agent creates a recipe plan, then calls the right MCP tools to set parameters

**deepagents concept explored:** Planning tool (`write_todos`), context offloading recipe state to a file artifact instead of the prompt, MCP tool integration via `langchain-mcp-adapters`.

---

### Phase 3 — Sub-agents (Task Delegation)
**Goal:** The orchestrator delegates specialized work to sub-agents.

#### Sub-agent A: Style Consultant
- Input: desired style name
- Output: recommended parameter ranges (OG, IBU, SRM, ABV)
- Tool: only `read_file` (reads from `src/data/styles.json`)
- System prompt: brewing judge persona, strict output format

#### Sub-agent B: Ingredient Analyst
- Input: list of fermentables + hops + yeast
- Output: flavor descriptor list per ingredient
- Tool: `read_file` on ingredient JSON databases
- System prompt: ingredient chemistry expert

#### Sub-agent C: Sensory Profiler
- Input: complete recipe + ingredient descriptors from sub-agent B
- Output: `SensoryProfile` (aroma, flavor, mouthfeel, appearance)
- Tool: `write_file` to cache the result
- System prompt: BJCP judge persona writing tasting notes

- [ ] Implement all three sub-agents in `src/agents/`
- [ ] Orchestrator uses deepagents `task` tool to spawn them
- [ ] `GET /recipe/{id}/profile` endpoint calls the profiler agent and returns cached result
- [ ] Integration test: full pipeline from "I want a hazy IPA" to sensory profile

**deepagents concept explored:** `task` tool for spawning sub-agents with isolated context windows, permission scoping so sub-agents only see the files they need.

---

### Phase 4 — Chat UI + Streaming
**Goal:** A minimal frontend so the agent interaction is tangible.

- [ ] `GET /chat/stream/{session_id}` — SSE endpoint wrapping LangGraph `.astream()`
- [ ] Simple HTML/JS chat page served at `/chat` (single static file, no framework)
- [ ] Show agent "thinking" steps (tool calls) as collapsible blocks
- [ ] Show the live `recipe.json` panel updated in real time

**deepagents concept explored:** LangGraph streaming, how token-by-token output maps to planning steps and tool results.

---

### Phase 5 — Persistent Memory
**Goal:** The agent remembers user preferences across sessions (e.g., "user always brews 20L, prefers English ales").

- [ ] Add LangGraph `MemoryStore` backend (SQLite-based)
- [ ] Orchestrator saves key user facts after each session using a `save_memory` tool
- [ ] Subsequent sessions start with injected user preference context
- [ ] Test: after a session where user mentions "I only have a 15L kettle", next session agent constrains batch sizes automatically

**deepagents concept explored:** Long-term memory via LangGraph store, cross-thread persistence.

---

### Phase 6 — Human-in-the-Loop
**Goal:** For destructive actions (delete recipe, change style completely), the agent asks for confirmation before executing.

- [ ] Configure `human-in-the-loop` on the `update_recipe` and `delete_recipe` MCP tools
- [ ] `PATCH /chat/{session_id}/approve` — resume endpoint after human approval
- [ ] UI shows a confirmation card before the agent writes changes

**deepagents concept explored:** LangGraph `interrupt`, human approval gates, resumable execution.

---

## File Layout (target state)

```
src/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py     # main recipe agent
│   ├── style_consultant.py # sub-agent A
│   ├── ingredient_analyst.py # sub-agent B
│   └── sensory_profiler.py # sub-agent C
├── data/
│   ├── fermentables.json
│   ├── hops.json
│   ├── yeasts.json
│   └── styles.json
├── endpoints/
│   ├── echo.py             # existing
│   ├── recipe.py           # Phase 1
│   └── chat.py             # Phase 4 (SSE)
├── models/
│   └── recipe.py           # TypedDicts
├── service/
│   └── recipe.py           # pure calculations
├── resources/
│   └── recipe.py           # aiosqlite CRUD
├── config.py               # add LLM keys, DB path
├── main.py
└── middleware.py
tests/
├── test_recipe_service.py  # calculation unit tests
├── test_recipe_endpoints.py
├── test_agents/
│   ├── test_orchestrator.py  # mock MCP tools
│   └── test_sensory_profiler.py
```

---

## Key Dependencies to Add

```toml
# production
"deepagents>=0.5.5"
"langchain-mcp-adapters>=0.2.0"
"langchain-openai>=0.3.0"   # or langchain-anthropic / langchain-google-genai
"aiosqlite>=0.20.0"

# dev / observability
"langsmith>=0.3.0"           # tracing
```

---

## Prompt Design Notes

Good prompts are the glue between agents. A few rules to follow:

1. **Orchestrator prompt**: "Before modifying any recipe parameter, always call `write_todos` with a numbered plan. Each step should reference a specific tool call. Only proceed after the plan is complete."
2. **Sub-agent prompts**: Be extremely narrow. "You are a hop aroma specialist. You receive a hop name and return a JSON object with keys: `aroma_descriptors`, `flavor_descriptors`, `typical_use`. Nothing else."
3. **Context injection pattern**: `"Current recipe state:\n{recipe_json}\n\nUser request: {user_message}"` — the recipe is always freshest from disk, never from memory.
4. **Output contracts**: Sub-agents always output structured JSON. The orchestrator validates before writing to the recipe.

---

## Learning Milestones

| Phase | What you learn |
|---|---|
| 0 | How deepagents' default harness prompt shapes model behavior |
| 1 | How FastMCP auto-generates MCP tools from FastAPI routes |
| 2 | Plan-first execution + context offloading to file artifacts |
| 3 | Sub-agent spawning, context isolation, delegation orchestration |
| 4 | LangGraph streaming + how agent steps map to UI events |
| 5 | Cross-session memory, LangGraph store backends |
| 6 | Human-in-the-loop, interrupt/resume patterns |

---

## Open Questions (to revisit per phase)

- Which LLM provider to use? (ollama for local dev, openai/anthropic for quality testing)
- Should the ingredient databases be tool-queryable (MCP tools) or purely file-read by agents?
- Do sub-agents need their own MCP endpoints, or does the file-read pattern suffice for Phase 3?
- At what point does the sensory profile warrant real retrieval (RAG over brewing literature) vs. pure LLM generation?
