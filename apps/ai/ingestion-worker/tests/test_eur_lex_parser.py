import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import HttpUrl

from ingestion_worker.domain.documents import LegalSubdivision, SourceDocument
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser


def test_parse_article_3_preserves_definition_hierarchy() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()

    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)

    article = next(article for article in document.articles if article.number == "3")

    assert len(article.provisions) == 1

    provision = article.provisions[0]

    assert len(provision.subdivisions) == 70
    assert provision.subdivisions[0].number == "1)"
    assert provision.subdivisions[0].list_type == "ARAB"
    assert provision.subdivisions[0].text.startswith("système d’IA")

    def flatten(subdivisions: list[LegalSubdivision]) -> list[LegalSubdivision]:
        result: list[LegalSubdivision] = []
        for subdivision in subdivisions:
            result.append(subdivision)
            result.extend(flatten(subdivision.children))
        return result

    all_subdivisions = flatten(provision.subdivisions)

    assert len(all_subdivisions) == 81
    assert sum(bool(item.children) for item in all_subdivisions) == 4
    assert all(item.text.strip() for item in all_subdivisions)
    assert all(item.number for item in all_subdivisions)


def test_inspect_formex_article_structures() -> None:
    from lxml import etree

    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    root = etree.fromstring(xml_content)

    articles = root.xpath(".//ENACTING.TERMS//ARTICLE")

    for article in articles:
        number = article.get("IDENTIFIER")
        title = article.findtext("./STI.ART")
        paragraphs = article.findall("./PARAG")
        direct_alineas = article.findall("./ALINEA")
        lists = article.xpath(".//LIST")

        if paragraphs or direct_alineas or lists:
            paragraph_details = [
                {
                    "number": paragraph.findtext("./NO.PARAG"),
                    "alineas": len(paragraph.findall("./ALINEA")),
                }
                for paragraph in paragraphs
            ]

            print(
                f"Article {number} | {title} | "
                f"paragraphs={len(paragraphs)} | "
                f"direct_alineas={len(direct_alineas)} | "
                f"lists={len(lists)} | "
                f"paragraph_details={paragraph_details}"
            )


def test_parse_article_2_preserves_paragraphs_and_subdivisions() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)
    article = next(item for item in document.articles if item.number == "2")

    assert article.title == "Champ d’application"
    assert len(article.provisions) == 13
    assert [provision.number for provision in article.provisions] == [
        f"{number}." for number in range(1, 14)
    ]
    assert all(provision.text or provision.subdivisions for provision in article.provisions)

    paragraph_1 = article.provisions[0]
    paragraph_13 = article.provisions[12]

    assert len(paragraph_1.subdivisions) == 7
    assert len(paragraph_13.subdivisions) == 2
    assert all(item.text.strip() for item in paragraph_1.subdivisions)
    assert all(item.text.strip() for item in paragraph_13.subdivisions)


def test_parse_article_32_preserves_direct_alinea() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)
    article = next(item for item in document.articles if item.number == "32")

    assert article.number == "32"
    assert article.provisions
    assert len(article.provisions) == 1

    provision = article.provisions[0]
    assert provision.number is None
    assert provision.text
    assert provision.subdivisions == []


def test_parse_article_75b_preserves_direct_alineas_and_lists() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)
    article = next(item for item in document.articles if item.number == "75B")

    assert article.number == "75B"
    assert len(article.provisions) == 1

    provision = article.provisions[0]
    assert provision.number is None
    assert provision.text
    assert len(provision.subdivisions) > 0
    assert all(item.text.strip() for item in provision.subdivisions)


def test_parse_articles_with_alphabetic_identifiers() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)
    article_numbers = {article.number for article in document.articles}

    assert {"4A", "60A", "75B"}.issubset(article_numbers)


def test_parse_document_preserves_all_article_identifiers() -> None:
    from lxml import etree

    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)

    root = etree.fromstring(xml_content)
    source_articles = root.xpath(".//ENACTING.TERMS//ARTICLE")
    source_identifiers = [element.get("IDENTIFIER") for element in source_articles]
    parsed_identifiers = [article.number for article in document.articles]

    assert len(parsed_identifiers) == len(source_identifiers)
    assert parsed_identifiers == [
        identifier.lstrip("0") if identifier and identifier[:3].isdigit() else identifier
        for identifier in source_identifiers
    ]
    assert len(parsed_identifiers) == len(set(parsed_identifiers))


def test_parse_document_normalizes_all_legal_text() -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        content_xml="",
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_content, source)

    def collect_texts(subdivisions: list[LegalSubdivision]) -> list[str]:
        texts: list[str] = []
        for subdivision in subdivisions:
            texts.append(subdivision.text)
            texts.extend(collect_texts(subdivision.children))
        return texts

    texts: list[str] = []

    for article in document.articles:
        if article.title:
            texts.append(article.title)

        for provision in article.provisions:
            if provision.text:
                texts.append(provision.text)

            texts.extend(collect_texts(provision.subdivisions))

    assert texts

    for text in texts:
        assert text == unicodedata.normalize("NFC", text)
        assert "\xa0" not in text
        assert "\u202f" not in text
        assert text == text.strip()
        assert not re.search(r"\s{2,}", text)
