from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Protocol, Self

from ai_service.contracts.tool_call_result import ToolCallResult, ToolDefinition


class ToolProvider(Protocol):
    async def list_tools(self) -> Sequence[ToolDefinition]: ...

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object],
    ) -> ToolCallResult: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    async def __aenter__(self) -> Self: ...
