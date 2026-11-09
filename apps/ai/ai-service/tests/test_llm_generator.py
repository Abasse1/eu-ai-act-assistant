from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import HttpUrl, ValidationError

from ai_service.agent.llm_generator import (
    InvalidGeneratedDocumentIndexError,
    LLMAnswerGenerator,
)
from ai_service.contracts.conversation import Citation
from ai_service.contracts.generation import GeneratedAnswerDraft
from ai_service.contracts.retrieval import RetrievedDocument


def create_document(reference: str, passage: str) -> RetrievedDocument:
    return RetrievedDocument(
        citation=Citation(
            reference=reference,
            passage=passage,
            document_title="EU AI Act",
            article="Regulation (EU) 2024/1689",
            version="2024-07-12",
            source_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
        ),
        score=0.92,
    )


def create_generator(
    result: GeneratedAnswerDraft | dict[str, object],
) -> tuple[LLMAnswerGenerator, Mock]:
    structured_model = Mock()
    structured_model.ainvoke = AsyncMock(return_value=result)

    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model

    generator = LLMAnswerGenerator(
        model=cast(BaseChatModel, model),
        language="fr",
    )

    return generator, structured_model


@pytest.mark.anyio
async def test_generate_returns_answer_with_original_document_citations() -> None:
    document_1 = create_document("Article 6", "High-risk AI systems.")
    document_2 = create_document("Article 9", "Risk management system.")

    generator, structured_model = create_generator(
        GeneratedAnswerDraft(
            can_answer=True,
            content="Les systèmes d'IA à haut risque sont soumis à des exigences.",
            used_document_indices=[1],
        )
    )

    answer = await generator.generate(
        question="Quelles sont les exigences applicables ?",
        documents=[document_1, document_2],
    )

    assert answer.content == "Les systèmes d'IA à haut risque sont soumis à des exigences."
    assert answer.citations == [document_2.citation]
    assert answer.disclaimer
    structured_model.ainvoke.assert_awaited_once()


@pytest.mark.anyio
async def test_generate_returns_abstention_when_model_cannot_answer() -> None:
    generator, structured_model = create_generator(
        GeneratedAnswerDraft(
            can_answer=False,
            content="",
            used_document_indices=[],
        )
    )

    answer = await generator.generate(
        question="Question without sufficient evidence",
        documents=[create_document("Article 6", "High-risk AI systems.")],
    )

    assert "suffisamment pertinentes" in answer.content
    assert answer.citations == []
    structured_model.ainvoke.assert_awaited_once()


@pytest.mark.anyio
async def test_generate_rejects_unknown_document_indices() -> None:
    generator, _ = create_generator(
        GeneratedAnswerDraft(
            can_answer=True,
            content="Unsupported answer.",
            used_document_indices=[1],
        )
    )

    with pytest.raises(InvalidGeneratedDocumentIndexError):
        await generator.generate(
            question="Question",
            documents=[create_document("Article 6", "High-risk AI systems.")],
        )


@pytest.mark.anyio
async def test_generate_rejects_invalid_structured_output() -> None:
    generator, _ = create_generator(
        {
            "can_answer": True,
            "content": "",
            "used_document_indices": [],
        }
    )

    with pytest.raises(ValidationError):
        await generator.generate(
            question="Question",
            documents=[create_document("Article 6", "High-risk AI systems.")],
        )


@pytest.mark.anyio
async def test_generate_abstains_without_calling_model_when_no_documents() -> None:
    generator, structured_model = create_generator(
        GeneratedAnswerDraft(
            can_answer=True,
            content="Unexpected answer.",
            used_document_indices=[0],
        )
    )

    answer = await generator.generate(
        question="Question",
        documents=[],
    )

    assert "suffisamment pertinentes" in answer.content
    assert answer.citations == []
    structured_model.ainvoke.assert_not_awaited()
