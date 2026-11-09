import pytest

from ai_service.contracts.conversation import Language
from ai_service.privacy.pii import PiiProtectionService


@pytest.fixture(scope="module")
def pii_service() -> PiiProtectionService:
    return PiiProtectionService()


@pytest.mark.parametrize(
    ("text", "language", "sensitive_value"),
    [
        ("Contactez-moi à jean@gamil.com", "fr", "jean@gmail.com"),
        ("Contact me at jean@gmail.com", "en", "jean@gmail.com"),
        ("Appelez moi au 06 12 34 56 78", "fr", "06 12 34 56 78"),
        ("Call me at +1 212 555 0198", "en", "+1 212 555 0198"),
    ],
)
def test_anonymize_personal_information(
    pii_service: PiiProtectionService, text: str, language: Language, sensitive_value: str
) -> None:
    anonymized = pii_service.anonymize(text, language)

    assert sensitive_value not in anonymized
    assert anonymized != text
