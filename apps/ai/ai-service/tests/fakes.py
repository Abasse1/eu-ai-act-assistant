from ai_service.contracts.conversation import AssistantAnswer
from ai_service.contracts.retrieval import RetrievedDocument
from ai_service.contracts.routing import RequestIntent, RequestRoutingResult


class FakeRequestRouter:
    def __init__(self, intent: RequestIntent) -> None:
        self._intent: RequestIntent = intent

    async def route(self, question: str) -> RequestRoutingResult:
        return RequestRoutingResult(intent=self._intent, reasoning="Intent provided by the test.")


class FakeDocumentRetriever:
    def __init__(self, documents: list[RetrievedDocument] | None = None) -> None:
        self._documents = documents or []
        self.questions: list[str] = []

    async def retrieve(self, question: str) -> list[RetrievedDocument]:
        self.questions.append(question)
        return self._documents


class FakeAnswerGenerator:
    def __init__(self, answer: AssistantAnswer | None = None) -> None:
        self._answer: AssistantAnswer = (
            answer
            if answer is not None
            else AssistantAnswer(
                content="Generated answer.",
                citations=[],
                disclaimer="Test disclaimer.",
            )
        )
        self.questions: list[str] = []
        self.documents: list[list[RetrievedDocument]] = []

    async def generate(
        self,
        question: str,
        documents: list[RetrievedDocument],
    ) -> AssistantAnswer:
        self.questions.append(question)
        self.documents.append(documents)
        return self._answer
