# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run development server
bash scripts/00_start.sh

# Run all tests with coverage
uv run pytest && uv run coverage report -m

# Run a single test
uv run pytest tests/test_main.py::test_root -v

# Lint and format
uv run ruff check .
uv run ruff format .
uv run ruff check --fix --unsafe-fixes  # auto-fix with type cleanup

# Type checking
uv run mypy .

# Pre-commit (runs ruff + mypy)
uv run pre-commit run --all-files

# Makefile shortcuts
make all       # deps + check + test
make check     # pre-commit run --all-files
make test      # pytest
make cov       # coverage with --fail-under enforcement
```

## Architecture

MCP server + REST API built with FastAPI, connecting LLMs to databases and internal APIs. Each MCP tool has an equivalent REST endpoint.

**Three layers:**
1. **Middleware** (`middleware.py`) - ASGI-level Bearer token auth with dual-mode support:
   - **Local dev** (`ENVIRONMENT=local`): Simple bearer token via `LOCAL_API_TOKEN` in `.env`
   - **Cloud envs** (`dev`/`qas`/`prod`): OAuth2 flow with Microsoft + Access BFF JWT validation
   - Public paths: `/`, `/health`, `/docs`, `/openapi.json`, `/login`, `/auth_microsoft`, `/callback`
2. **Orchestration Layer** - Specialist LLM that interprets user intent, routes to correct endpoints with proper parameters, applies guardrails
3. **Resource Layer** - Executes queries and API calls with no AI logic. Each resource has its own rate limit

**Data flow per module** (e.g., oracle, expeditus):
`endpoints/<module>.py` (route + validation) -> `service/<module>.py` (business logic) -> `resources/<module>.py` (DB/API calls)

- **Endpoints** define FastAPI routes, query validation, and per-endpoint rate limits via `dependencies.rate_limit()`
- **Services** contain pure functions that transform data; oracle services load SQL from `sql/*.sql` files at import time
- **Resources** handle external I/O: `resources/oracle.py` manages an oracledb `SessionPool` singleton (`DBManager`), `resources/expeditus.py` makes async httpx calls

**Rate limiting:** Each endpoint creates its own independent limiter via `rate_limit(max_requests, window)` in `dependencies.py`. Uses per-IP sliding window.

**Config:** `config.py` uses pydantic-settings (`Settings` class) loading from `.env`. Singleton via `settings = Settings.model_validate({})`.

**External resources:**

None currently. When adding a new resource:
- Create `src/resources/<module>.py` for all external I/O (DB connections, HTTP clients)
- Use `httpx.AsyncClient` for outbound HTTP; manage lifecycle via FastAPI lifespan
- Add connection settings to `src/config.py` (`Settings` class)
- Mock or monkeypatch the resource layer in tests — never hit real external systems in CI

**Authentication:**

`BearerTokenMiddleware` in `middleware.py` (ASGI-level, applied globally):
- **Public paths** — `/`, `/health`, `/docs`, `/openapi.json` bypass auth entirely
- **`ENVIRONMENT=local`** — validates the `Authorization: Bearer <token>` header against `LOCAL_API_TOKEN` from `.env`
- **Cloud envs** (`dev`/`qas`/`prod`) — middleware passes through (placeholder for JWT/OAuth2 validation)

To add a new public path, append it to `UNPROTECTED_PATHS` in `middleware.py`.

## Code Standards

**Type safety:**
- No `dict[str, Any]` or `JSONResponse` for structured payloads
- Use `TypedDict` for all structured entities (API payloads, DB documents, configs)
- Use `BaseModel` for FastStream message broker schemas
- Modern syntax: `str | None`, `dict`, `list` (not `Optional`, `Dict`, `List`)

**Testing:**
- Naming: `test_<function>_<scenario>` (e.g., `test_price_schema_when_valid_payload`)
- Every FastAPI endpoint needs at least a smoke test
- Minimum 70% coverage (enforced in `pyproject.toml`)

**Style:**
- KISS over OOP: prefer pure functions and dataclasses
- `async def` for all I/O-bound routes
- Structured logging with loguru
- Ruff config in `ruff.toml`: UP040 is ignored (mypy CI compatibility), isort uses `force-single-line`, `ARG` rules are relaxed in tests

---

## React Frontend (`frontend/`)

### Stack (locked — do not deviate)
- **Vite + React 18 + TypeScript** — `strict: true` in `tsconfig.json`
- **Tailwind CSS** — all styling via utility classes; no inline `style=` props, no CSS modules
- **shadcn/ui** — UI primitives (Button, Input, Table, Dialog, etc.); add with `npx shadcn@latest add <component>`; never copy styles manually
- **TanStack Query v5** (React Query) — all server state; no raw `useEffect + fetch` patterns
- **React Router v6** — declarative routes in `App.tsx`

### Commands
```bash
cd frontend
npm run dev        # Vite dev server on :5173, proxies /api → FastAPI :8000
npm run build      # TypeScript check + Vite build → dist/
npm run lint       # ESLint
```

### File structure (enforced)
```
frontend/src/
  api/        ← one file per backend resource; all fetch() calls live here only
  components/ ← reusable UI pieces; no page-level logic or data fetching
  pages/      ← one file per route; composes components, owns query calls
  types/      ← TypeScript types mirroring backend models exactly
  hooks/      ← custom hooks (useRecipe, useChat, useSession)
  lib/        ← pure utilities (sse.ts, utils.ts)
```

### Absolute rules
- **No `any` types** — use `unknown` + type guard if type is genuinely unknown
- **All API response types** must mirror backend TypedDicts from `src/models/recipe.py` exactly (same field names, same nesting)
- **One named export per file** — no default exports; name matches the filename
- **Components over ~100 lines must be split**
- **No prop drilling beyond 2 levels** — use React Context for auth token and session state
- **All mutations must invalidate** the relevant query key immediately: `queryClient.invalidateQueries({ queryKey: ['recipe', id] })`
- **SSE stream lives exclusively in `hooks/useChat.ts`** — never inline stream handling in a component

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
