from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ToolCallResult:
    is_error: bool
    structured_content: Mapping[str, object] | None = None
    text_content: tuple[str, ...] = ()
