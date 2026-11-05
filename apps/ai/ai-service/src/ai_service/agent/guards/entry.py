from ai_service.agent.state import AssistantTurnState
from ai_service.privacy.pii import PiiProtectionService


class InvalidUserInputError(ValueError):
    """Raised when the user input cannot be processed safely."""


def guard_entry(
    state: AssistantTurnState,
    pii_service: PiiProtectionService,
    language: str,
) -> AssistantTurnState:
    question = state["question"].strip()

    if not question:
        raise InvalidUserInputError("The question must not be empty.")

    anonymized_question = pii_service.anonymize(question, language)

    return {
        **state,
        "question": anonymized_question,
    }
