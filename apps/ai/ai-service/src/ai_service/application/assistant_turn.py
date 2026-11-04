from collections.abc import AsyncIterator

from typing_extensions import Protocol

from ai_service.contracts.conversation import AssistantTurnRequest
from ai_service.contracts.streaming import StreamEvent


class AssistantTurnProcessor(Protocol):
    def stream(
        self,
        request: AssistantTurnRequest,
        idempotency_key: str,
    ) -> AsyncIterator[StreamEvent]:
        """Process an assistant turn and stream its events."""
        ...
