from typing import Literal

from ai_service.contracts.conversation import Language


StandardResponseType = Literal[
    "clarification",
    "out_of_scope",
    "insufficient_sources",
    "registry_action_unavailable",
]

RESPONSE: dict[str, dict[Language, str]] = {
    "clarification": {
        "fr": "Votre demande nécessite des précisions. Pouvez-vous apporter davantage de contexte ?",
        "en": "Your request needs clarification. Could you provide more context?",
    },
    "out_of_scope": {
        "fr": (
            "Je suis spécialisé dans l'AI Act européen et la conformité des systèmes "
            "d'intelligence artificielle. Je ne peux pas traiter cette demande dans mon "
            "périmètre actuel."
        ),
        "en": (
            "I specialize in the European AI Act and AI system compliance. "
            "I cannot address this request within my current scope."
        ),
    },
    "insufficient_sources": {
        "fr": (
            "Je ne dispose pas de sources réglementaires suffisamment pertinentes pour "
            "répondre de manière fiable à votre question. Vous pouvez reformuler votre "
            "demande ou préciser le contexte."
        ),
        "en": (
            "I don't have sufficiently relevant regulatory sources to answer your question "
            "reliably. You can rephrase your request or provide additional context."
        ),
    },
    "registry_action_unavailable": {
        "fr": (
            "La gestion du registre des systèmes d'intelligence artificielle "
            "n'est pas encore disponible."
        ),
        "en": "AI system registry management is not available yet.",
    },
}


DISCLAIMER: dict[Language, str] = {
    "fr": (
        "Cette réponse est une aide à la compréhension de l'AI Act "
        "et ne constitue pas un avis juridique."
    ),
    "en": (
        "This response is intended to help understand the AI Act "
        "and does not constitute legal advice."
    ),
}


def get_standard_response(intent: StandardResponseType, language: Language) -> str:
    return RESPONSE[intent][language]


def get_standard_disclaimer(language: Language) -> str:
    return DISCLAIMER[language]
