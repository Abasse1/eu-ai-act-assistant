import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from ai_service.agent.generation import validate_answer_citations
from ai_service.agent.guards.entry import InvalidUserInputError
from ai_service.agent.guards.injection import PromptInjectionDetectedError
from ai_service.agent.guards.pipeline import guard_input
from ai_service.agent.responses import (
    StandardResponseType,
    get_standard_disclaimer,
    get_standard_response,
)
from ai_service.agent.routing import RequestRouter
from ai_service.agent.state import AssistantTurnState
from ai_service.contracts.conversation import Language
from ai_service.contracts.generation import AnswerGenerator
from ai_service.contracts.routing import RequestIntent
from ai_service.contracts.streaming import FieldEvent
from ai_service.privacy.pii import PiiAnonymizer
from ai_service.security.prompt_injection import PromptInjectionDetector
from langgraph.graph.state import CompiledStateGraph
from ai_service.agent.retrieval import DocumentRetriever


def route_by_intent(state: AssistantTurnState) -> RequestIntent:
    intent = state.get("intent")

    if intent is None:
        raise ValueError("Request intent is missing from the assistant state.")

    return intent


def route_after_retrieval(state: AssistantTurnState) -> Literal["generate", "abstain"]:
    return "generate" if state.get("retrieved_documents") else "abstain"


def route_after_input_guard(
    state: AssistantTurnState,
) -> Literal["continue", "stop"]:
    return "stop" if state.get("failure") is not None else "continue"


def build_assistant_graph(
    pii_service: PiiAnonymizer,
    injection_detector: PromptInjectionDetector,
    language: Language,
    router: RequestRouter,
    retriever: DocumentRetriever,
    answer_generator: AnswerGenerator,
) -> CompiledStateGraph[AssistantTurnState, None, AssistantTurnState, AssistantTurnState]:
    async def input_guard_node(state: AssistantTurnState) -> AssistantTurnState:
        try:
            return await asyncio.to_thread(
                guard_input,
                state=state,
                pii_service=pii_service,
                injection_detector=injection_detector,
                language=language,
            )
        except InvalidUserInputError:
            return {
                **state,
                "failure": FieldEvent(
                    code="request_rejected",
                    message="Veuillez saisir une question valide.",
                    retryable=False,
                ),
            }
        except PromptInjectionDetectedError:
            return {
                **state,
                "failure": FieldEvent(
                    code="request_rejected",
                    message="Cette demande ne peut pas être traitée. Reformulez votre question.",
                    retryable=False,
                ),
            }

    async def routing_node(state: AssistantTurnState) -> AssistantTurnState:
        result = await router.route(state["question"])
        return {**state, "intent": result.intent}

    async def regulatory_question_node(state: AssistantTurnState) -> AssistantTurnState:
        documents = await retriever.retrieve(state["question"])
        return {**state, "retrieved_documents": documents}

    async def registry_action_node(state: AssistantTurnState) -> AssistantTurnState:
        return standard_answer(state, "registry_action_unavailable")

    async def clarification_node(state: AssistantTurnState) -> AssistantTurnState:
        return standard_answer(state, "clarification")

    async def out_of_scope_node(state: AssistantTurnState) -> AssistantTurnState:
        return standard_answer(state, "out_of_scope")

    async def generation_node(state: AssistantTurnState) -> AssistantTurnState:
        documents = state.get("retrieved_documents", [])
        answer = await answer_generator.generate(question=state["question"], documents=documents)
        validate_answer_citations(answer, documents)

        return {
            **state,
            "answer": answer.content,
            "citations": answer.citations,
            "disclaimer": answer.disclaimer,
        }

    async def insufficient_sources_node(state: AssistantTurnState) -> AssistantTurnState:
        return standard_answer(state, "insufficient_sources")

    def standard_answer(
        state: AssistantTurnState, response_type: StandardResponseType
    ) -> AssistantTurnState:
        return {
            **state,
            "answer": get_standard_response(response_type, language),
            "citations": [],
            "disclaimer": get_standard_disclaimer(language),
        }

    graph: StateGraph[
        AssistantTurnState,
        None,
        AssistantTurnState,
        AssistantTurnState,
    ] = StateGraph(AssistantTurnState)
    graph.add_node(input_guard_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(routing_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(regulatory_question_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(registry_action_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(clarification_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(out_of_scope_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(generation_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node(insufficient_sources_node)  # pyright: ignore[reportUnknownMemberType]

    graph.add_edge(START, "input_guard_node")

    graph.add_conditional_edges(
        "input_guard_node",
        route_after_input_guard,
        {
            "continue": "routing_node",
            "stop": END,
        },
    )

    graph.add_conditional_edges(
        "routing_node",
        route_by_intent,
        {
            "regulatory_question": "regulatory_question_node",
            "registry_action": "registry_action_node",
            "clarification": "clarification_node",
            "out_of_scope": "out_of_scope_node",
        },
    )

    graph.add_conditional_edges(
        "regulatory_question_node",
        route_after_retrieval,
        {"generate": "generation_node", "abstain": "insufficient_sources_node"},
    )
    graph.add_edge("generation_node", END)
    graph.add_edge("registry_action_node", END)
    graph.add_edge("insufficient_sources_node", END)
    graph.add_edge("clarification_node", END)
    graph.add_edge("out_of_scope_node", END)

    return graph.compile()  # pyright: ignore[reportUnknownMemberType]
