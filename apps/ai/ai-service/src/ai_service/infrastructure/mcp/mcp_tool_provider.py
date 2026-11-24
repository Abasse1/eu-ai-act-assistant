from collections.abc import Mapping, Sequence
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Self

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ai_service.application.ports.tool_provider import ToolProvider
from ai_service.contracts.tool_call_result import ToolCallResult, ToolDefinition


class McpToolProvider(ToolProvider):
    def __init__(self, server_url: str) -> None:
        self._server_url = server_url
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("MCP client is already connected.")

        stack = AsyncExitStack()
        await stack.__aenter__()

        try:
            read_stream, write_stream = await stack.enter_async_context(
                streamable_http_client(self._server_url)
            )

            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

            await session.initialize()

        except BaseException:
            await stack.aclose()
            raise

        self._exit_stack = stack
        self._session = session

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._session = None

        if self._exit_stack is None:
            return False

        stack = self._exit_stack
        self._exit_stack = None

        return await stack.__aexit__(exc_type, exc_value, traceback)

    def _get_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP client is not connected.")

        return self._session

    async def list_tools(self) -> Sequence[ToolDefinition]:
        response = await self._get_session().list_tools()

        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description or "",
                input_schema=(
                    getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", {})
                ),
            )
            for tool in response.tools
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object],
    ) -> ToolCallResult:
        response = await self._get_session().call_tool(
            name=name,
            arguments=dict(arguments),
        )

        structured_content = getattr(response, "structured_content", None) or getattr(
            response, "structuredContent", None
        )

        text_content = tuple(
            text
            for block in response.content
            if isinstance((text := getattr(block, "text", None)), str)
        )

        return ToolCallResult(
            is_error=bool(getattr(response, "is_error", getattr(response, "isError", False))),
            structured_content=(
                structured_content if isinstance(structured_content, Mapping) else None
            ),  # type: ignore
            text_content=text_content,
        )
