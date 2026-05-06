# Python Development Template

A modern Python project template following current best practices as of 2026.

## ✨ Features

- **Modern Python packaging** with `pyproject.toml`
- **Dependency management** with `uv` for faster dependency resolution
- **Code quality tools**: Ruff for linting and formatting, mypy for type checking
- **Pre-commit hooks** for automated code quality checks
- **Testing setup** with pytest and coverage reporting
- **UV environment** management
- **Makefile** for common development tasks

## 🛠️ Installation

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

uv --version
```

### Quick Start

```bash
# Run the default setup (creates env, syncs dependencies, installs pre-commit)
make
```

### Available Make Commands

```bash
make              # Default: setup environment, sync deps, install hooks
make deps         # Sync dependencies and install pre-commit hooks (uv sync + pre-commit install)
make check        # Run pre-commit hooks against all files
make test         # Run tests with pytest
make cov          # Run coverage (erase, run, and report)
make clean        # Clean cache and build artifacts
```

## 🏗️ Architecture

FastAPI app with an auto-generated FastMCP server mounted at `/mcp`.

```
src/
├── main.py              # FastAPI app + FastMCP mount + lifespan
├── config.py            # pydantic-settings (Settings singleton)
├── middleware.py        # ASGI Bearer token auth
├── dependencies.py      # Rate limiter factory (per-IP sliding window)
├── exceptions.py        # App exception hierarchy (400 / 404 / 500)
├── exception_handlers.py# Register exception handlers
└── endpoints/
    └── echo.py          # Example route (GET /echo)
```

### Three-Layer Pattern

New modules follow a strict separation:

| Layer | Location | Responsibility |
|---|---|---|
| Endpoints | `src/endpoints/<module>.py` | Route definition, request validation, rate limits |
| Service | `src/service/<module>.py` | Business logic, pure functions, data transforms |
| Resources | `src/resources/<module>.py` | External I/O: DB queries, HTTP calls |

Data flows strictly top-down: `endpoints → service → resources`. Services never import from endpoints; resources never import from services.

### MCP

`FastMCP.from_fastapi(app)` auto-generates MCP tools from all FastAPI routes. Run the MCP server standalone:

```bash
bash scripts/01_start_mcp.sh
```

## 📝 License

MIT License - feel free to use this template for your projects!

---
