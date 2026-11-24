from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ai_service.api.sse import create_sse_response
from ai_service.application.ports.assistant_turn import AssistantTurnProcessor
from ai_service.contracts.conversation import AssistantTurnRequest

router = APIRouter(prefix="/conversations", tags=["Assistant"])


@router.post(
    "/{conversation_id}/messages",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a message to the assistant",
    description=(
        "Processes a user message and streams the assistant's response using "
        "Server-Sent Events (SSE).\n\n"
        "The assistant analyzes the request, retrieves relevant EU AI Act "
        "provisions when applicable, and generates a grounded response.\n\n"
        "The stream can contain the following events:\n"
        "- `content.delta`: response content.\n"
        "- `citation`: a regulatory source supporting the response.\n"
        "- `completed`: the complete assistant answer.\n"
        "- `field`: a processing or validation error.\n\n"
        "The stream terminates when the assistant completes processing or "
        "returns an error event."
    ),
    operation_id="createAssistantMessage",
    responses={
        200: {
            "description": "Assistant response streamed through Server-Sent Events.",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "description": "A stream of Server-Sent Events.",
                    }
                }
            },
        },
        400: {"description": "The conversation identifier does not match the request."},
        422: {"description": "The request body or required headers are invalid."},
    },
)
async def create_message(
    conversation_id: UUID,
    body: AssistantTurnRequest,
    request: Request,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Unique key identifying this assistant turn.",
        min_length=1,
    ),
) -> StreamingResponse:
    if body.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation ID does not match the request.",
        )

    processor: AssistantTurnProcessor = request.app.state.assistant_turn_processor

    return create_sse_response(processor.stream(body, idempotency_key))
