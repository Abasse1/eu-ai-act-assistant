import logging
from collections.abc import AsyncIterator, Awaitable
from typing import Callable, cast

from langgraph.graph.state import CompiledStateGraph

from ai_service.agent.state import AssistantTurnState
from ai_service.application.assistant_turn import AssistantTurnProcessor, AsyncAssistantGraph
from ai_service.contracts.conversation import AssistantAnswer, AssistantTurnRequest
from ai_service.contracts.streaming import (
    CompletedEvent,
    ContentEvent,
    CitationEvent,
    FieldEvent,
    StreamEvent,
)

logger = logging.getLogger(__name__)


class LangGraphAssistantTurnProcessor(AssistantTurnProcessor):
    def __init__(
        self,
        graph: CompiledStateGraph[
            AssistantTurnState,
            None,
            AssistantTurnState,
            AssistantTurnState,
        ],
    ) -> None:
        self._graph: AsyncAssistantGraph = cast(AsyncAssistantGraph, graph)

    async def stream(
        self,
        request: AssistantTurnRequest,
        idempotency_key: str,
    ) -> AsyncIterator[StreamEvent]:
        initial_state: AssistantTurnState = {
            "organization_id": str(request.organization_id),
            "user_id": str(request.user_id),
            "conversation_id": str(request.conversation_id),
            "message_id": str(request.message_id),
            "question": request.content,
        }

        try:
            invoke = cast(
                Callable[[AssistantTurnState], Awaitable[AssistantTurnState]],
                self._graph.ainvoke,
            )
            result = await invoke(initial_state)

            failure = result.get("failure")
            if failure is not None:
                yield failure
                return

            content = result.get("answer")
            disclaimer = result.get("disclaimer")

            if content is None or disclaimer is None:
                logger.error(
                    "Assistant graph completed without a valid answer. Conversation ID: %s",
                    request.conversation_id,
                )
                yield FieldEvent(
                    code="processing_failed",
                    message="The assistant could not produce a valid response.",
                    retryable=False,
                )
                return

            answer = AssistantAnswer(
                content=content,
                citations=result.get("citations", []),
                disclaimer=disclaimer,
            )

            if answer.content:
                yield ContentEvent(content=answer.content)

            for citation in answer.citations:
                yield CitationEvent(citation=citation)

            yield CompletedEvent(answer=answer)

        except Exception:
            logger.exception(
                "Assistant turn processing failed. Conversation ID: %s",
                request.conversation_id,
            )
            yield FieldEvent(
                code="processing_failed",
                message="An error occurred while processing your request.",
                retryable=False,
            )
