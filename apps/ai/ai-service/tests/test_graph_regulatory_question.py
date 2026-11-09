from unittest.mock import AsyncMock, Mock
from uuid import UUID

from pydantic import HttpUrl
import pytest

from ai_service.agent.generation import InvalidAnswerCitationError
from ai_service.agent.graph import build_assistant_graph
from ai_service.agent.state import AssistantTurnState
from ai_service.contracts.conversation import AssistantAnswer, Citation
from ai_service.contracts.retrieval import RetrievedDocument
from ai_service.contracts.routing import RequestRoutingResult
from langgraph.graph.state import CompiledStateGraph
from ai_service.agent.state import AssistantTurnState


def create_state(question: str) -> AssistantTurnState:
    return {
        "organization_id": str(UUID(int=1)),
        "user_id": str(UUID(int=2)),
        "conversation_id": str(UUID(int=3)),
        "message_id": str(UUID(int=4)),
        "question": question,
    }


def create_citation() -> Citation:
    return Citation(
        reference="Article 6",
        passage="Classification rules for high-risk AI systems.",
        document_title="Regulation (EU) 2024/1689",
        article="Article 6",
        version="2024",
        source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    )


def create_graph(
    retriever: Mock,
    answer_generator: Mock,
) -> tuple[
    CompiledStateGraph[
        AssistantTurnState,
        None,
        AssistantTurnState,
        AssistantTurnState,
    ],
    Mock,
]:
    pii_service = Mock()
    pii_service.anonymize.side_effect = lambda text, language: text

    injection_detector = Mock()
    injection_detector.detect.return_value = False

    router = Mock()
    router.route = AsyncMock(
        return_value=RequestRoutingResult(
            intent="regulatory_question",
            reasoning="The user asks about regulatory requirements.",
        )
    )

    graph = build_assistant_graph(
        pii_service=pii_service,
        injection_detector=injection_detector,
        language="en",
        router=router,
        retriever=retriever,
        answer_generator=answer_generator,
    )

    return graph, router


@pytest.mark.anyio
async def test_regulatory_question_generates_grounded_answer() -> None:
    citation = create_citation()
    document = RetrievedDocument(citation=citation, score=0.95)

    retriever = Mock()
    retriever.retrieve = AsyncMock(return_value=[document])

    answer_generator = Mock()
    answer_generator.generate = AsyncMock(
        return_value=AssistantAnswer(
            content="The classification rules are defined in Article 6.",
            citations=[citation],
            disclaimer="This answer is informational and does not constitute legal advice.",
        )
    )

    graph, router = create_graph(retriever, answer_generator)
    question = "What are the high-risk AI classification rules?"

    result = await graph.ainvoke(create_state(question))

    assert result["intent"] == "regulatory_question"
    assert result["answer"] == "The classification rules are defined in Article 6."
    assert result["citations"] == [citation]
    assert result["disclaimer"] == answer_generator.generate.return_value.disclaimer

    router.route.assert_awaited_once_with(question)
    retriever.retrieve.assert_awaited_once_with(question)
    answer_generator.generate.assert_awaited_once()


@pytest.mark.anyio
async def test_regulatory_question_abstains_when_no_documents_are_found() -> None:
    retriever = Mock()
    retriever.retrieve = AsyncMock(return_value=[])

    answer_generator = Mock()
    answer_generator.generate = AsyncMock()

    graph, router = create_graph(retriever, answer_generator)
    question = "What are the high-risk AI classification rules?"

    result = await graph.ainvoke(create_state(question))

    assert result["intent"] == "regulatory_question"
    assert result["answer"]
    assert result["citations"] == []
    assert result["disclaimer"]

    router.route.assert_awaited_once()
    retriever.retrieve.assert_awaited_once_with(question)
    answer_generator.generate.assert_not_awaited()


@pytest.mark.anyio
async def test_regulatory_question_rejects_unsupported_citations() -> None:
    retrieved_citation = create_citation()
    unsupported_citation = Citation(
        reference="Article 9",
        passage="Requirements for risk management.",
        document_title="Regulation (EU) 2024/1689",
        article="Article 9",
        version="2024",
        source_url= HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    )

    retriever = Mock()
    retriever.retrieve = AsyncMock(
        return_value=[RetrievedDocument(citation=retrieved_citation, score=0.95)]
    )

    answer_generator = Mock()
    answer_generator.generate = AsyncMock(
        return_value=AssistantAnswer(
            content="The requirements are defined in Article 9.",
            citations=[unsupported_citation],
            disclaimer="Legal disclaimer.",
        )
    )

    graph, _ = create_graph(retriever, answer_generator)

    with pytest.raises(InvalidAnswerCitationError):
        await graph.ainvoke(create_state("What are the risk management requirements?"))

    answer_generator.generate.assert_awaited_once()
