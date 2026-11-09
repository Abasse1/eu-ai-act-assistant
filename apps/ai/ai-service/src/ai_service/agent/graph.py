from typing import Literal

from langgraph.graph import END, START, StateGraph

from ai_service.agent.generation import valid_answer_citations
from ai_service.agent.guards.pipeline import guard_input
from ai_service.agent.responses import get_standard_reponse
from ai_service.agent.routing import RequestRouter
from ai_service.agent.state import AssistantTurnState
from ai_service.contracts.conversation import Language
from ai_service.contracts.generation import AnswerGenerator
from ai_service.contracts.routing import RequestIntent
from ai_service.privacy.pii import PiiProtectionService
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


def build_assistant_graph(
    pii_service: PiiProtectionService,
    injection_detector: PromptInjectionDetector,
    language: Language,
    router: RequestRouter,
    retriever: DocumentRetriever,
    answer_generator: AnswerGenerator,
) -> CompiledStateGraph[AssistantTurnState, None, AssistantTurnState, AssistantTurnState]:
    async def input_guard_node(state: AssistantTurnState) -> AssistantTurnState:
        return guard_input(
            state=state,
            pii_service=pii_service,
            injection_detector=injection_detector,
            language=language,
        )

    async def routing_node(state: AssistantTurnState) -> AssistantTurnState:
        result = await router.route(state["question"])
        return {**state, "intent": result.intent}

    async def regulatory_question_node(state: AssistantTurnState) -> AssistantTurnState:
        documents = await retriever.retrieve(state["question"])
        return {**state, "retrieved_documents": documents}

    async def registry_action_node(state: AssistantTurnState) -> AssistantTurnState:
        return state

    async def clarification_node(state: AssistantTurnState) -> AssistantTurnState:
        return {**state, "answer": get_standard_reponse("clarification", language), "citations": []}

    async def out_of_scope_node(state: AssistantTurnState) -> AssistantTurnState:
        return {**state, "answer": get_standard_reponse("out_of_scope", language), "citations": []}

    async def generation_node(state: AssistantTurnState) -> AssistantTurnState:
        documents = state.get("retrieved_documents", [])
        answer = await answer_generator.generate(question=state["question"], documents=documents)
        valid_answer_citations(answer, documents)

        return {**state, "answer": answer.content, "citations": answer.citations}

    async def insufficient_sources_node(state: AssistantTurnState) -> AssistantTurnState:
        return {
            **state,
            "answer": get_standard_reponse("insufficient_sources", language),
            "citations": [],
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
    graph.add_edge("input_guard_node", "routing_node")

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
