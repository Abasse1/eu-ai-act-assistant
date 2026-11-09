from ai_service.agent.guards.entry import guard_entry
from ai_service.agent.guards.injection import guard_prompt_injection
from ai_service.agent.state import AssistantTurnState
from ai_service.contracts.conversation import Language
from ai_service.privacy.pii import PiiProtectionService
from ai_service.security.prompt_injection import PromptInjectionDetector


def guard_input(
    state: AssistantTurnState,
    pii_service: PiiProtectionService,
    injection_detector: PromptInjectionDetector,
    language: Language,
) -> AssistantTurnState:
    guard_state = guard_entry(state, pii_service, language)

    return guard_prompt_injection(guard_state, injection_detector)
