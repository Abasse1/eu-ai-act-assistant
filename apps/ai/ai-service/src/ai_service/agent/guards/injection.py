from ai_service.agent.guards.entry import InvalidUserInputError
from ai_service.agent.state import AssistantTurnState
from ai_service.security.prompt_injection import PromptInjectionDetector


def guard_prompt_injection(
    state: AssistantTurnState, decorator: PromptInjectionDetector
) -> AssistantTurnState:

    if decorator.detect(state["question"]):
        raise InvalidUserInputError("The request contains potentially malicious instructions.")

    return state
