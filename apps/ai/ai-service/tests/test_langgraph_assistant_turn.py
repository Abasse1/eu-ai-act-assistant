from uuid import UUID

from pydantic import HttpUrl
import pytest

from ai_service.agent.state import AssistantTurnState
from ai_service.application.langgraph_assistant_turn import (
    LangGraphAssistantTurnProcessor,
)
from ai_service.contracts.conversation import (
    AssistantTurnRequest,
    Citation,
)
from ai_service.contracts.streaming import (
    CitationEvent,
    CompletedEvent,
    ContentEvent,
    FieldEvent,
)


class FakeGraph:
    def __init__(self, result: AssistantTurnState | Exception) -> None:
        self._result = result
        self.received_state: AssistantTurnState | None = None

    async def ainvoke(self, input: AssistantTurnState) -> AssistantTurnState:
        self.received_state = input

        if isinstance(self._result, Exception):
            raise self._result

        return self._result


def create_request() -> AssistantTurnRequest:
    return AssistantTurnRequest(
        organization_id=UUID(int=1),
        user_id=UUID(int=2),
        conversation_id=UUID(int=3),
        message_id=UUID(int=4),
        content="What are the requirements of the EU AI Act?",
    )


def create_citation() -> Citation:
    return Citation(
        reference="Article 6",
        passage="Classification rules for high-risk AI systems.",
        document_title="Regulation (EU) 2024/1689",
        article="Article 6",
        version="2024",
        source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    )


def create_state(
    answer: str,
    citations: list[Citation] | None = None,
    disclaimer: str = "Test disclaimer.",
) -> AssistantTurnState:
    return {
        "organization_id": str(UUID(int=1)),
        "user_id": str(UUID(int=2)),
        "conversation_id": str(UUID(int=3)),
        "message_id": str(UUID(int=4)),
        "question": "What are the requirements of the EU AI Act?",
        "answer": answer,
        "citations": citations or [],
        "disclaimer": disclaimer,
    }


async def collect_events(
    processor: LangGraphAssistantTurnProcessor,
    request: AssistantTurnRequest,
) -> list[ContentEvent | CitationEvent | CompletedEvent | FieldEvent]:
    events = processor.stream(request, idempotency_key="test-key")
    return [event async for event in events]


@pytest.mark.anyio
async def test_stream_returns_answer_with_citations() -> None:
    citation = create_citation()
    graph = FakeGraph(
        create_state(
            answer="This is a regulatory answer.",
            citations=[citation],
            disclaimer="Legal disclaimer.",
        )
    )
    processor = LangGraphAssistantTurnProcessor(graph)  # type: ignore[arg-type]

    events = await collect_events(processor, create_request())

    assert len(events) == 3
    assert isinstance(events[0], ContentEvent)
    assert events[0].content == "This is a regulatory answer."
    assert isinstance(events[1], CitationEvent)
    assert events[1].citation == citation
    assert isinstance(events[2], CompletedEvent)
    assert events[2].answer.content == "This is a regulatory answer."
    assert events[2].answer.citations == [citation]
    assert events[2].answer.disclaimer == "Legal disclaimer."


@pytest.mark.anyio
async def test_stream_returns_standard_answer_without_citations() -> None:
    graph = FakeGraph(
        create_state(
            answer="I need more context to answer your question.",
            citations=[],
        )
    )
    processor = LangGraphAssistantTurnProcessor(graph)  # type: ignore[arg-type]

    events = await collect_events(processor, create_request())

    assert len(events) == 2
    assert isinstance(events[0], ContentEvent)
    assert isinstance(events[1], CompletedEvent)
    assert events[1].answer.citations == []
    assert events[1].answer.disclaimer == "Test disclaimer."


@pytest.mark.anyio
async def test_stream_returns_processing_failed_when_graph_raises() -> None:
    graph = FakeGraph(RuntimeError("Internal database connection details"))
    processor = LangGraphAssistantTurnProcessor(graph)  # type: ignore[arg-type]

    events = await collect_events(processor, create_request())

    assert len(events) == 1
    assert isinstance(events[0], FieldEvent)
    assert events[0].code == "processing_failed"
    assert events[0].retryable is False
    assert "Internal database" not in events[0].message
