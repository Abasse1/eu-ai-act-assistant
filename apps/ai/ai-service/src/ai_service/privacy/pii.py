from typing import Any, cast

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult as AnonymizerRecognizerResult
from presidio_analyzer.predefined_recognizers import EmailRecognizer, PhoneRecognizer
from presidio_anonymizer.entities import OperatorConfig


def _create_anonymizer() -> Any:
    return AnonymizerEngine()  # type: ignore[no-untyped-call]


class PiiProtectionService:
    def __init__(self) -> None:
        configuration: dict[str, Any] = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"},
                {"lang_code": "fr", "model_name": "fr_core_news_md"},
            ],
        }

        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        registry = RecognizerRegistry(supported_languages=["en", "fr"])
        registry.load_predefined_recognizers(languages=["en"])

        registry.add_recognizer(
            EmailRecognizer(
                supported_language="fr",
                context=["email", "courriel", "adresse électronique"],
            )
        )
        registry.add_recognizer(
            PhoneRecognizer(
                supported_language="fr",
                context=["téléphone", "portable", "mobile", "numéro"],
            )
        )

        self._analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=nlp_engine,
            supported_languages=["en", "fr"],
        )
        self._anonymizer = _create_anonymizer()

    def anonymize(self, text: str, language: str) -> str:
        if language not in {"en", "fr"}:
            raise ValueError(f"Unsupported language: {language}")

        results = self._analyzer.analyze(text=text, language=language)

        anonymizer_results = [
            AnonymizerRecognizerResult(
                entity_type=item.entity_type,
                start=item.start,
                end=item.end,
                score=item.score,
            )
            for item in results
        ]

        result = self._anonymizer.anonymize(
            text=text,
            analyzer_results=anonymizer_results,
            operators={
                "DEFAULT": OperatorConfig(
                    "replace",
                    {"new_value": "<PERSONAL_DATA>"},
                ),
            },
        )

        return cast(str, result.text)
