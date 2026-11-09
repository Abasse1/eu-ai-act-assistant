from typing import Protocol

from ai_service.contracts.routing import RequestRoutingResult


class RequestRouter(Protocol):
    async def route(self, question: str) -> RequestRoutingResult:
        """Determine the business intent of a user request."""
        ...
