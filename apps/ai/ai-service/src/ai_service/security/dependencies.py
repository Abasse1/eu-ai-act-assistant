from wrapt import lru_cache

from ai_service.security.huggingface_detector import HuggingFacePromptInjectionDetector
from ai_service.security.prompt_injection import PromptInjectionDetector


@lru_cache(mawsize=1)
def get_prompt_injection_decorator() -> PromptInjectionDetector:
    return HuggingFacePromptInjectionDetector()
