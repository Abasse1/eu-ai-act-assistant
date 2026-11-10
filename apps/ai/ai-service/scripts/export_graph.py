
from pathlib import Path

from ai_service.agent.graph import build_assistant_graph
from ai_service.contracts.conversation import AssistantAnswer, Language
from ai_service.contracts.retrieval import RetrievedDocument
from ai_service.contracts.routing import RequestRoutingResult
from langchain_core.runnables.graph import NodeStyles

class FakePiiAnonymizer:
    def anonymize(self, text: str, language: Language) -> str:
        return text


class FakePromptInjectionDetector:
    def detect(self, text: str) -> bool:
        return False


class FakeRequestRouter:
    async def route(self, question: str) -> RequestRoutingResult:
        raise NotImplementedError("Graph export only.")


class FakeDocumentRetriever:
    async def retrieve(self, question: str) -> list[RetrievedDocument]:
        raise NotImplementedError("Graph export only.")


class FakeAnswerGenerator:
    async def generate(self, question: str, documents: list[RetrievedDocument]) -> AssistantAnswer:
        raise NotImplementedError("Graph export only.")


def main() -> None:
    graph = build_assistant_graph(
        pii_service=FakePiiAnonymizer(),
        injection_detector=FakePromptInjectionDetector(),
        language="fr",
        router=FakeRequestRouter(),
        retriever=FakeDocumentRetriever(),
        answer_generator=FakeAnswerGenerator(),
    )
  
    output_path = Path("../../../docs/architecture/langgraph/assistant_graph.png")
    output_path.parent.mkdir(parents=False, exist_ok=True)
    graph_image = graph.get_graph().draw_mermaid_png(
    node_colors=NodeStyles(
        default="fill:#DBEAFE,stroke:#2563EB,color:#1E293B",
        first="fill:#E0E7FF,stroke:#4F46E5,color:#1E1B4B",
        last="fill:#DCFCE7,stroke:#16A34A,color:#14532D",
    ),
    background_color="white",
)

    output_path.write_bytes(graph_image)
    print(f"Graph exported to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
