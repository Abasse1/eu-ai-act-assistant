from transformers import TextClassificationPipeline, pipeline

from ai_service.application.ports.prompt_injection import PromptInjectionDetector


class HuggingFacePromptInjectionDetector(PromptInjectionDetector):
    def __init__(self, model_path: str, threshold: float = 0.85) -> None:
        self._threshold = threshold
        self._classifier: TextClassificationPipeline = pipeline(
            "text-classification",
            model=model_path,
            tokenizer=model_path,
            truncation=True,
            device=-1
        )

    def detect(self, text: str) -> bool:
        result = self._classifier(text, top_k=1)[0]
        label = str(result["label"]).upper()
        score = float(result["score"])
        return label == "INJECTION" and score >= self._threshold