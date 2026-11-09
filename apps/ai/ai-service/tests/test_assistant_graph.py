from typing import Any, Awaitable, cast

from pydantic import HttpUrl
import pytest

from ai_service.agent.generation import InvalidAnswerCitationError
from ai_service.agent.graph import build_assistant_graph
from ai_service.agent.state import AssistantTurnState
from ai_service.contracts.conversation import AssistantAnswer, Citation
from ai_service.contracts.retrieval import RetrievedDocument
from ai_service.contracts.routing import RequestIntent
from ai_service.privacy.pii import PiiProtectionService
from tests.fakes import FakeAnswerGenerator, FakeDocumentRetriever, FakeRequestRouter


class FakePiiProtectionService(PiiProtectionService):
    def __init__(self) -> None:
        pass

    def anonymize(self, text: str, language: str) -> str:
        return text


class FakePromptinjectionDecorator:
    def detect(self, text: str) -> bool:
        return False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("intent", "expected_content"),
    [
        ("clarification", "nécessite des précisions"),
        ("out_of_scope", "spécialisé dans l'AI Act européen"),
    ],
)
async def test_assistant_graph_returns_expected_response_for_non_rag_intents(
    intent: RequestIntent, expected_content: str
) -> None:
    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter(intent),
        language="fr",
        retriever=FakeDocumentRetriever(),
        answer_generator=FakeAnswerGenerator(),
    )

    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "Can you help me?",
    }

    result = await graph.ainvoke(initial_state)  # pyright: ignore[reportUnknownMemberType]

    assert expected_content in result["answer"]
    assert result["citations"] == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "intent",
    ["regulatory_question", "registry_action", "clarification", "out_of_scope"],
)
async def test_assistant_graph_preserves_routed_intent(intent: RequestIntent) -> None:
    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter(intent),
        language="fr",
        retriever=FakeDocumentRetriever(),
        answer_generator=FakeAnswerGenerator(),
    )

    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "What are the obligations under the EU AI Act?",
    }

    result = await graph.ainvoke(initial_state)  # pyright: ignore[reportUnknownMemberType]

    assert result["intent"] == intent


@pytest.mark.anyio
async def test_regulatory_question_retrieves_documents_and_generates_answer() -> None:
    citation = Citation(
        reference="Article 6",
        passage="High-risk AI systems are subject to specific requirements.",
        article="Regulation (EU) 2024/1689",
        version="2024-07-12",
        source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    )

    document = RetrievedDocument(citation=citation, score=0.92)
    retriever = FakeDocumentRetriever([document])

    expected_answer = AssistantAnswer(
        content="High-risk AI systems are subject to specific requirements.",
        citations=[citation],
        disclaimer="This answer is based on the retrieved regulatory sources.",
    )
    answer_generator = FakeAnswerGenerator(expected_answer)

    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter("regulatory_question"),
        retriever=retriever,
        answer_generator=answer_generator,
        language="en",
    )

    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "What are the requirements for high-risk AI systems?",
    }

    result = await graph.ainvoke(initial_state)  # pyright: ignore[reportUnknownMemberType]

    assert result["retrieved_documents"] == [document]
    assert result["answer"] == expected_answer.content
    assert result["citations"] == [citation]
    assert retriever.questions == [initial_state["question"]]
    assert answer_generator.questions == [initial_state["question"]]
    assert answer_generator.documents == [[document]]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "intent",
    ["registry_action", "clarification", "out_of_scope"],
)
async def test_non_regulatory_intents_do_not_trigger_retrieval_or_generation(
    intent: RequestIntent,
) -> None:
    retriever = FakeDocumentRetriever()
    answer_generator = FakeAnswerGenerator()

    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter(intent),
        retriever=retriever,
        answer_generator=answer_generator,
        language="fr",
    )

    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "Can you help me?",
    }

    await graph.ainvoke(initial_state)  # pyright: ignore[reportUnknownMemberType]

    assert retriever.questions == []
    assert answer_generator.questions == []
    assert answer_generator.documents == []


@pytest.mark.anyio
async def test_regulatory_question_rejects_unsupported_citations() -> None:
    unsupported_citation = Citation(
        reference="Article 99",
        passage="Unsupported regulatory passage",
        article="Regulation (EU) 2024/1689",
        version="2024-07-12",
        source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    )

    answer_generator = FakeAnswerGenerator(
        AssistantAnswer(
            content="According to article 99, this system is prohited.",
            citations=[unsupported_citation],
            disclaimer="Test disclaimer",
        )
    )
    retriever = FakeDocumentRetriever(
        [
            RetrievedDocument(
                citation=Citation(
                    reference="Article 6",
                    passage="High-risk AI systems are subject to specific requirements.",
                    article="Regulation (EU) 2024/1689",
                    version="2024-07-12",
                    source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
                ),
                score=0.92,
            )
        ]
    )
    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter("regulatory_question"),
        retriever=retriever,
        answer_generator=answer_generator,
        language="en",
    )

    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "What are the requirements for high-risk Ai systems?",
    }

    with pytest.raises(InvalidAnswerCitationError):
        await cast(Awaitable[dict[str, Any]], graph.ainvoke(initial_state))  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.anyio
async def test_regulatory_question_without_documents_returns_abstention() -> None:
    retriever = FakeDocumentRetriever()
    answer_generator = FakeAnswerGenerator()
    graph = build_assistant_graph(
        pii_service=FakePiiProtectionService(),
        injection_detector=FakePromptinjectionDecorator(),
        router=FakeRequestRouter("regulatory_question"),
        retriever=retriever,
        answer_generator=answer_generator,
        language="fr",
    )
    initial_state: AssistantTurnState = {
        "organization_id": "org-001",
        "user_id": "user-001",
        "conversation_id": "conversation-001",
        "message_id": "message-001",
        "question": "What are the requirements for high-risk AI systems?",
    }

    result = await graph.ainvoke(initial_state)  # pyright: ignore[reportUnknownMemberType]

    assert "suffisamment pertinentes" in result["answer"]
    assert result["citations"] == []
    assert retriever.questions == [initial_state["question"]]
    assert answer_generator.questions == []
