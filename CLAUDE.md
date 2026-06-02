# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run development server
bash scripts/00_start.sh

# Run all tests with coverage
uv run pytest && uv run coverage report -m

# Run a single test
uv run pytest tests/test_recipe_service.py::test_calc_og -v

# Lint and format
uv run ruff check .
uv run ruff format .
uv run ruff check --fix --unsafe-fixes  # auto-fix with type cleanup

# Type checking
uv run mypy .

# Pre-commit (runs ruff + mypy + bandit)
uv run pre-commit run --all-files

# Makefile shortcuts
make all       # deps + check + test
make check     # pre-commit run --all-files
make test      # pytest
make cov       # coverage with --fail-under enforcement
```

## Architecture

Homebrewing recipe assistant: FastAPI backend + FastMCP server (auto-generated from FastAPI routes) + LangGraph/deepagents orchestrator + React frontend.

**Three layers:**
1. **Middleware** (`middleware.py`) — ASGI-level Bearer token auth:
   - **Local dev** (`ENVIRONMENT=local`): validates `Authorization: Bearer <token>` against `LOCAL_API_TOKEN` from `.env`
   - **Cloud envs** (`dev`/`qas`/`prod`): passthrough — add JWT/OAuth2 validation here
   - Public paths: `/`, `/health`, `/docs`, `/openapi.json`
2. **Agent layer** (`src/agents/`) — LangGraph orchestrator + deepagents sub-agents. Reads/writes recipes via MCP tools. System prompt in `orchestrator.py`.
3. **Resource layer** (`src/resources/`) — aiosqlite CRUD, no AI logic. Each resource owns its DB schema init.

**Data flow:**
`endpoints/<module>.py` (route + validation) → `service/<module>.py` (pure business logic) → `resources/<module>.py` (DB/IO)

Modules: `recipe`, `equipment`, `chat`, `echo`.

**MCP:**
`FastMCP.from_fastapi(app)` auto-generates MCP tools from all FastAPI routes at startup. Mounted at `/mcp`. The agent connects to it via `MultiServerMCPClient` using streamable HTTP. In `ENVIRONMENT=local`, `httpx_client_kwargs` passes the Bearer token so internal ASGI calls clear middleware.

**Config:** `config.py` uses pydantic-settings (`Settings`) loading from `.env`. Key vars: `ENVIRONMENT`, `LOCAL_API_TOKEN`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `LLM_PROVIDER`, `LLM_MODEL`, `ANTHROPIC_API_KEY`, `MCP_BASE_URL`, `DB_PATH`.

**Authentication:**

`BearerTokenMiddleware` in `middleware.py` (ASGI-level, applied globally):
- **Public paths** — `/`, `/health`, `/docs`, `/openapi.json` bypass auth entirely
- **`ENVIRONMENT=local`** — validates `Authorization: Bearer <token>` against `LOCAL_API_TOKEN`
- **Cloud envs** — passthrough (add your JWT logic there)

To add a public path, append it to `_PUBLIC_PATHS` in `middleware.py`.

**LLM / model selection** (`src/agents/base.py`):
- `ENVIRONMENT=local` → `ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)`
- Cloud → `"{LLM_PROVIDER}:{LLM_MODEL}"` string resolved by langchain (e.g. `anthropic:claude-sonnet-4-6`)

## Code Standards

**Type safety:**
- No `dict[str, Any]` or `JSONResponse` for structured payloads
- Use `TypedDict` for all structured entities (API payloads, DB rows, configs)
- Modern syntax: `str | None`, `dict`, `list` (not `Optional`, `Dict`, `List`)

**Testing:**
- Naming: `test_<function>_<scenario>` (e.g., `test_calculate_grain_bill_guinness_target_og`)
- Every FastAPI endpoint needs at least a smoke test
- Minimum 70% coverage (enforced in `pyproject.toml`)

**Style:**
- KISS over OOP: prefer pure functions and TypedDicts
- `async def` for all I/O-bound routes
- Structured logging with loguru
- Ruff config in `ruff.toml`: UP040 ignored (mypy compatibility), isort `force-single-line`, ARG rules relaxed in tests

---

## React Frontend (`frontend/`)

### Stack (locked — do not deviate)
- **Vite + React 18 + TypeScript** — `strict: true` in `tsconfig.app.json`
- **Tailwind CSS v4** — all styling via utility classes; no inline `style=` props, no CSS modules
- **shadcn/ui (Base UI)** — UI primitives; add with `npx shadcn@latest add <component>`; never copy styles manually. Base UI has no `asChild` prop — use `render=` instead.
- **TanStack Query v5** — all server state; no raw `useEffect + fetch` patterns
- **React Router v7** — declarative routes in `App.tsx`

### Commands
```bash
cd frontend
npm install          # install deps (required before first build)
npm run dev          # Vite dev server on :5173, proxies /api → FastAPI :8000
npm run build        # TypeScript check + Vite build → dist/
npm run lint         # ESLint
```

### File structure (enforced)
```
frontend/src/
  api/        ← one file per backend resource; all fetch() calls live here only
  components/ ← reusable UI pieces; no page-level logic or data fetching
  pages/      ← one file per route; composes components, owns query calls
  types/      ← TypeScript types mirroring backend TypedDicts exactly
  hooks/      ← custom hooks (useRecipe, useChat, useSession)
  lib/        ← pure utilities (sse.ts, utils.ts)
```

### Absolute rules
- **No `any` types** — use `unknown` + type guard if type is genuinely unknown
- **All API response types** must mirror backend TypedDicts from `src/models/recipe.py` exactly (same field names, same nesting)
- **One named export per file** — no default exports; name matches the filename
- **Components over ~100 lines must be split**
- **All mutations must invalidate** the relevant query key immediately: `queryClient.invalidateQueries({ queryKey: ['recipe', id] })`
- **SSE stream lives exclusively in `hooks/useChat.ts`** — never inline stream handling in a component
- **Token SSE events are JSON-encoded** — always `JSON.parse(data)` when handling `event: token`

### Data fetching
- `useQuery` for GETs, `useMutation` for POST/PATCH/DELETE
- Query keys: `['recipes']` for list, `['recipe', id]` for single, `['notes', id]` for brew notes
- After any PATCH, invalidate `['recipe', id]` so stats and all fields refresh atomically

### Styling
- Tailwind utility classes only; use `cn()` from `lib/utils.ts` (shadcn convention) for conditional classes
- No arbitrary values like `w-[372px]` unless no Tailwind equivalent exists

### Error handling
- Wrap every page in `<ErrorBoundary>`
- Surface API errors via React Query's `error` state — display inline or in a toast
- Never swallow errors with empty `catch {}` blocks

### Auth
- API token read from `import.meta.env.VITE_API_TOKEN` (set in `frontend/.env.local`, gitignored)
- Every request goes through `api/client.ts` which injects `Authorization: Bearer {token}`
- Never hardcode the token
