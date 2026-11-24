from typing import Protocol


class PromptInjectionDetector(Protocol):
    def detect(self, text: str) -> bool:
        """Return whether the input contains a prompt injection attempt."""
        ...
