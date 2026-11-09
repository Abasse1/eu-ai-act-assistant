from typing import Literal

from ai_service.contracts.conversation import Language


RESPONSE: dict[str, dict[Language, str]] = {
    "clarification": {
        "fr": "Votre demande nécessite des précisions. Pouvez-vous apporter davantage de contexte?",
        "en": "Your request requires clarification. Could you provide additional context?",
    },
    "out_of_scope": {
        "fr": "Je suis spécialisé dans l'AI Act européen et la conformité des systèmes d'intéligence artificielle. Je ne peux pas traiter cette demande dans mon périmètre actuel.",
        "en": "I specilize in the European AI Act and AI system compliance. I cannot address this request within my current scope.",
    },
    "insufficient_sources": {
        "fr": "Je ne dispose pas de sources réglementaires suffisamment pertinentes pour répondre de manière fiable à votre question. Vous pouvez reformuler votre demande ou préciser le contexte.",
        "en": "I don't have sufficiently relevant regulatory sources to answer your question reliably. You can rephrase your request or provide additional context.",
    },
}


def get_standard_reponse(
    intent: Literal["clarification", "out_of_scope", "insufficient_sources"], language: Language
) -> str:
    return RESPONSE[intent][language]
