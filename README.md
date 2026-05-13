# BrewAgent

An AI-powered beer recipe assistant built on a planning-first agent architecture. Design recipes in natural language via chat, or edit fields directly — the agent and the UI are both first-class ways to work with the same recipe.

## What it does

- **Chat with an agent** to design, refine, and analyse beer recipes
- **Live recipe panel** — OG, FG, ABV, IBU, and SRM update after every agent patch or manual edit
- **Editable recipe fields** — fermentables, hops, yeast, style, and batch size all editable by hand
- **Sensory profiling** — one-click analysis of aroma, flavour, mouthfeel, and appearance
- **Brew notes** — agent writes working notes to disk; shown in a collapsible Markdown panel
- **Session persistence** — conversation history survives server restarts; browser reconnects to the same thread after a page refresh
- **HITL confirmation** — agent describes planned changes and waits for your approval before patching
- **Rich domain knowledge** — BJCP styles, hop pairing, yeast profiles, water chemistry, fermentation science, and ingredient substitutions loaded as agent skills

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + FastMCP (auto-generates MCP tools from REST routes) |
| Agent | deepagents (LangGraph) with `MemorySaver` → `AsyncSqliteSaver` |
| LLM | Anthropic Claude (cloud) or Ollama (local) — set by `ENVIRONMENT` |
| Frontend | Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui + TanStack Query v5 |
| Database | aiosqlite (recipes) + `langgraph-checkpoint-sqlite` (conversation history) |

---

## Quick start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node 20+ with npm
- An Anthropic or OpenAI API key (or a running Ollama instance)

### 1 — Backend

```bash
# Copy and fill in credentials
cp .env.example .env

# Install Python deps + pre-commit hooks
make

# Start the FastAPI server (port 8000)
bash scripts/00_start.sh
```

### 2 — Frontend

```bash
# Create the frontend env file
echo "VITE_API_TOKEN=test-token" > frontend/.env.local

# Install JS deps
cd frontend && npm install

# Start the dev server (port 5173)
bash scripts/03_start_frontend.sh
```

Open [http://localhost:5173](http://localhost:5173).

> The Vite dev server proxies `/api/*` to `http://localhost:8000` so there are no CORS issues.

### 3 — Gradio UI (legacy)

The original Gradio interface is still available as a fallback:

```bash
bash scripts/02_start_ui.sh   # port 7860
```

---

## Environment variables

Copy `.env.example` and set the values for your environment.

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `local` | `local` uses Ollama + simple bearer auth; `dev`/`prod` uses Anthropic + OAuth2 |
| `LOCAL_API_TOKEN` | `test-token` | Bearer token for local auth (matches `VITE_API_TOKEN` in frontend) |
| `ANTHROPIC_API_KEY` | — | Required when `ENVIRONMENT != local` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint (local only) |
| `OLLAMA_MODEL` | `llama3.2` | Model name for Ollama |
| `DB_PATH` | `brew.db` | SQLite file for recipes |
| `CHECKPOINT_DB_PATH` | `brew_checkpoints.db` | SQLite file for conversation history |
| `MCP_BASE_URL` | `http://localhost:8000` | Base URL the agent uses to reach the MCP endpoint |

---

## Architecture

### Three-layer backend

```
src/endpoints/<module>.py   ← route + validation + rate limiting
src/service/<module>.py     ← pure business logic (calculations, transforms)
src/resources/<module>.py   ← external I/O (aiosqlite, HTTP)
```

Data flows strictly top-down. Services never import endpoints; resources never import services.

### Agent design — four principles

| Principle | What it means |
|---|---|
| **Planning-first** | Agent calls `write_todos` before modifying any recipe field |
| **Context offloading** | Live recipe state stays in the DB, accessed via MCP tools — never in the prompt |
| **Task delegation** | Orchestrator routes to specialist sub-agents: Style Consultant, Ingredient Analyst, Sensory Profiler |
| **Prompting matters** | Every agent has a tightly scoped system prompt with explicit tool names and output contracts |

### MCP self-referential loop

`FastMCP.from_fastapi(app)` auto-generates MCP tools from all FastAPI routes. The agent connects back to its own server's `/mcp` endpoint via `MultiServerMCPClient`, so recipe CRUD tools require zero extra code beyond the REST endpoints.

### Project layout

```
src/
├── agents/
│   ├── orchestrator.py     # recipe_agent_context + MemorySaver/AsyncSqliteSaver
│   ├── subagents.py        # STYLE_CONSULTANT, INGREDIENT_ANALYST, SENSORY_PROFILER
│   └── base.py             # get_model() — Ollama or Anthropic
├── endpoints/
│   ├── recipe.py           # CRUD + /profile + /notes + /styles
│   └── chat.py             # POST /chat SSE stream
├── models/                 # TypedDicts: Recipe, RecipeWithStats, ChatRequest, …
├── resources/recipe.py     # aiosqlite CRUD
├── service/recipe.py       # OG/IBU/SRM/FG/ABV calculations
├── ui/app.py               # Gradio fallback UI
└── data/
    ├── styles.json          # 34 BJCP styles
    ├── fermentables.json    # ~50 entries
    ├── hops.json            # ~40 entries
    └── yeasts.json          # ~22 strains

data/skills/                 # Agent skill files (YAML frontmatter required)
├── bjcp-styles/SKILL.md
├── hop-pairing/SKILL.md
├── yeast-profiles/SKILL.md
├── ingredient-substitutions/SKILL.md
├── fermentation-science/SKILL.md
└── water-chemistry/SKILL.md

frontend/src/
├── api/          # Typed fetch wrappers (one file per resource)
├── components/   # Reusable UI pieces
├── hooks/        # useRecipe, useChat, useSession
├── lib/          # sse.ts (SSE stream parser), utils.ts
├── pages/        # RecipeListPage, RecipeDetailPage
└── types/        # TypeScript types mirroring backend TypedDicts exactly
```

---

## Development

```bash
# Run all tests with coverage
uv run pytest && uv run coverage report -m

# Lint + type check
make check

# Frontend type check + build
cd frontend && npm run build

# Single test
uv run pytest tests/test_recipe_service.py -v
```

### Key scripts

| Script | What it does |
|---|---|
| `scripts/00_start.sh` | Start FastAPI on port 8000 |
| `scripts/01_start_mcp.sh` | Start MCP server standalone |
| `scripts/02_start_ui.sh` | Start Gradio UI on port 7860 |
| `scripts/03_start_frontend.sh` | Start React dev server on port 5173 |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/recipe` | Create recipe |
| `GET` | `/recipe/{id}` | Get recipe with calculated stats |
| `PATCH` | `/recipe/{id}` | Partial update |
| `GET` | `/recipes` | List all recipes (with stats) |
| `GET` | `/recipes/styles` | List BJCP styles |
| `GET` | `/recipe/{id}/notes` | Get brew notes (Markdown) |
| `GET` | `/recipe/{id}/profile` | Generate sensory profile via agent |
| `POST` | `/chat` | SSE stream — agent conversation |

All endpoints require `Authorization: Bearer <token>`.

**SSE event types** from `POST /chat`:

| Event | Data |
|---|---|
| `token` | Raw text chunk (stream as-is to UI) |
| `tool_call` | JSON `{name, input}` |
| `done` | *(empty)* |
| `error` | Error string |

---

## License

MIT
