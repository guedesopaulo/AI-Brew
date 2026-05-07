"""FastAPI application + FastMCP server."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastmcp import FastMCP
from loguru import logger

from src.config import settings
from src.endpoints.chat import router as chat_router
from src.endpoints.echo import router as echo_router
from src.endpoints.recipe import router as recipe_router
from src.exception_handlers import register_exception_handlers
from src.middleware import BearerTokenMiddleware
from src.resources.recipe import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    _ = app
    await init_db(settings.DB_PATH)
    os.makedirs("brew_notes", exist_ok=True)
    async with mcp_app.router.lifespan_context(mcp_app):
        logger.info("startup complete")
        yield
        logger.info("shutdown complete")


app = FastAPI(
    title="AI-Brew",
    version="0.1.0",
    swagger_ui_parameters={"displayRequestDuration": True},
    lifespan=lifespan,
)

register_exception_handlers(app)
app.add_middleware(BearerTokenMiddleware)
app.include_router(echo_router)
app.include_router(recipe_router)
app.include_router(chat_router)

# MCP: auto-generate tools from all FastAPI routes
mcp = FastMCP.from_fastapi(app, name="python-dev")
mcp_app = mcp.http_app(transport="http", path="/")
app.mount("/mcp", mcp_app)


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def redirect_to_docs() -> str:
    return "/docs"


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)  # nosec B104


if __name__ == "__main__":
    main()
