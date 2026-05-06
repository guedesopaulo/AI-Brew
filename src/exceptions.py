"""Application exception hierarchy."""

from fastapi import HTTPException


class AppServerError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=500, detail=detail)


class AppRequestError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


class AppNotFoundError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, detail=detail)
