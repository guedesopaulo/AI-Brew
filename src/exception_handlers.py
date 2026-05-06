"""Register FastAPI exception handlers."""

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from src.exceptions import AppNotFoundError
from src.exceptions import AppRequestError
from src.exceptions import AppServerError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppServerError)
    async def server_error_handler(
        request: Request, exc: AppServerError
    ) -> JSONResponse:
        _ = request
        logger.error("AppServerError: {}", exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(AppRequestError)
    async def request_error_handler(
        request: Request, exc: AppRequestError
    ) -> JSONResponse:
        _ = request
        logger.warning("AppRequestError: {}", exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(AppNotFoundError)
    async def not_found_handler(
        request: Request, exc: AppNotFoundError
    ) -> JSONResponse:
        _ = request
        logger.warning("AppNotFoundError: {}", exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
        logger.warning("{}: {}", request.url, exc_str)
        return JSONResponse(status_code=422, content={"detail": exc_str})
