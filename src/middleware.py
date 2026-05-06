"""ASGI Bearer token middleware.

Local dev  (ENVIRONMENT=local): validates against LOCAL_API_TOKEN from .env.
Other envs (dev/qas/prod):      passthrough — add your auth logic here.

Public paths (no auth required):
    GET /
    GET /health
    GET /docs
    GET /openapi.json
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.types import ASGIApp

from src.config import settings

_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json"}


class BearerTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        if settings.ENVIRONMENT != "local":
            # Cloud envs: plug in your JWT / OAuth2 validation here
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                status_code=401, content={"detail": "Missing Bearer token."}
            )

        token = auth.removeprefix("Bearer ").strip()
        if token != settings.LOCAL_API_TOKEN:
            return JSONResponse(status_code=403, content={"detail": "Invalid token."})

        return await call_next(request)
