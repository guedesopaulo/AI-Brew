"""Per-endpoint rate limiter dependency.

Usage in an endpoint module:
    _my_rate_limit = rate_limit(max_requests=30, window=60)

    @router.get("/something", dependencies=[Depends(_my_rate_limit)])
    async def my_endpoint() -> ...:
        ...
"""

import time
from collections import defaultdict
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException
from fastapi import Request


def rate_limit(max_requests: int, window: int) -> Callable[[Request], None]:
    """Return a FastAPI dependency that enforces a per-IP sliding window rate limit.

    Args:
        max_requests: Maximum number of requests allowed within the window.
        window: Time window in seconds.
    """
    requests: dict[str, deque[float]] = defaultdict(deque)

    def _limiter(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        queue = requests[ip]
        while queue and now - queue[0] > window:
            queue.popleft()
        if len(queue) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {max_requests} requests per {window}s.",
            )
        queue.append(now)

    return _limiter
