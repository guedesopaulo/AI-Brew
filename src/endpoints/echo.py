"""
Echo endpoint — dummy module to demonstrate
the endpoints → service → resources pattern.
"""

from typing import TypedDict

from fastapi import APIRouter
from fastapi import Query
from loguru import logger

router = APIRouter(prefix="/echo", tags=["echo"])


class EchoResponse(TypedDict):
    message: str


@router.get("")
async def echo(
    message: str = Query(description="Message to echo back."),
) -> EchoResponse:
    """Echo the given message back to the caller."""
    logger.info("echo called with message={!r}", message)
    return {"message": message}
