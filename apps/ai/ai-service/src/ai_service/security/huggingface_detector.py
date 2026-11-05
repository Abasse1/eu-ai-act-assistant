from transformers import TextClassificationPipeline, pipeline


class HuggingFacePromptInjectionDetector:
    def __init__(
        self, model_name: str = "Horizon-Labs/prompt-injection-guard-small", threshold: float = 0.85
    ) -> None:
        self._threshold = threshold
        self._classifier: TextClassificationPipeline = pipeline(
            "text-classification", model=model_name, tokenizer=model_name, truncation=True
        )

    def detect(self, text: str) -> bool:
        result = self._classifier(text, top_k=1)[0]
        label = str(result["label"]).upper()
        score = float(result["score"])

        return label == "INJECTION" and score >= self._threshold
