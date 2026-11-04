from collections.abc import AsyncIterable

from fastapi.responses import StreamingResponse

from ai_service.contracts.streaming import StreamEvent


def encode_sse(event: StreamEvent) -> str:
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


async def encode_sse_stream(events: AsyncIterable[StreamEvent]) -> AsyncIterable[str]:
    async for event in events:
        yield encode_sse(event)


def create_sse_response(events: AsyncIterable[StreamEvent]) -> StreamingResponse:
    return StreamingResponse(
        content=encode_sse_stream(events),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "X-Accel-Buffering": "no"},
    )
