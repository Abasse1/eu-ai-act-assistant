from ai_service.agent.state import AssistantTurnState
from ai_service.security.prompt_injection import PromptInjectionDetector


class PromptInjectionDetectedError(ValueError):
    """Raised when a prompt injection attempt is detected."""


def guard_prompt_injection(
    state: AssistantTurnState,
    detector: PromptInjectionDetector,
) -> AssistantTurnState:
    if detector.detect(state["question"]):
        raise PromptInjectionDetectedError(
            "The request contains potentially malicious instructions."
        )

    return state
