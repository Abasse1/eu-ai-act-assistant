import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from lxml import etree
from pydantic import HttpUrl

from ingestion_worker.domain.documents import (
    LegalBlock,
    LegalSubdivision,
    SourceDocument,
    StructuredLegalDocument,
)
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser


@pytest.fixture
def french_document():
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    xml_metadata = Path("tests/fixtures/formex/ai-act-fr.doc.xml").read_bytes()

    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        retrieved_at=datetime.now(UTC),
    )

    return EurLexParser().parse(xml_metadata, xml_content, source)


def test_parse_article_3_preserves_definition_hierarchy(
    french_document: StructuredLegalDocument,
) -> None:

    document = french_document

    article = next(article for article in document.articles if article.number == "3")

    assert len(article.provisions) == 1

    provision = article.provisions[0]

    assert len(provision.alineas[0].subdivisions) == 70
    assert provision.alineas[0].subdivisions[0].number == "1)"
    assert provision.alineas[0].subdivisions[0].list_type == "ARAB"
    assert provision.alineas[0].subdivisions[0].text.startswith("système d’IA")

    def flatten(subdivisions: list[LegalSubdivision]) -> list[LegalSubdivision]:
        result: list[LegalSubdivision] = []
        for subdivision in subdivisions:
            result.append(subdivision)
            result.extend(flatten(subdivision.children))
        return result

    all_subdivisions = flatten(provision.alineas[0].subdivisions)

    assert len(all_subdivisions) == 81
    assert sum(bool(item.children) for item in all_subdivisions) == 4
    assert all(item.text.strip() for item in all_subdivisions)
    assert all(item.number for item in all_subdivisions)

    assert len(document.annexes) == 14
    assert document.annexes[0].title.startswith("ANNEXE I")
    assert document.annexes[0].blocks

    annex_xiv = document.annexes[13]
    tables = find_blocks(annex_xiv.blocks, "TBL")

    assert len(tables) == 6
    assert all(table.attributes["COLS"] == "2" for table in tables)
    assert all(table.attributes["NO.SEQ"] for table in tables)

    rows = find_blocks(annex_xiv.blocks, "ROW")
    cells = find_blocks(annex_xiv.blocks, "CELL")

    assert len(rows) == 28
    assert len(cells) == 56


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
            paragraph_details: list[dict[str, object]] = [
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


def test_parse_article_2_preserves_paragraphs_and_subdivisions(
    french_document: StructuredLegalDocument,
) -> None:

    document = french_document
    article = next(item for item in document.articles if item.number == "2")

    assert article.title == "Champ d’application"
    assert len(article.provisions) == 13
    assert [provision.number for provision in article.provisions] == [
        f"{number}." for number in range(1, 14)
    ]
    assert all(
        provision.alineas[0].text or provision.alineas[0].subdivisions
        for provision in article.provisions
    )

    paragraph_1 = article.provisions[0]
    paragraph_13 = article.provisions[12]

    assert len(paragraph_1.alineas[0].subdivisions) == 7
    assert len(paragraph_13.alineas[0].subdivisions) == 2
    assert all(item.text for item in paragraph_1.alineas)
    assert all(item.text for item in paragraph_13.alineas)


def test_parse_article_32_preserves_direct_alinea(french_document: StructuredLegalDocument) -> None:
    document = french_document
    article = next(item for item in document.articles if item.number == "32")

    assert article.number == "32"
    assert article.provisions
    assert len(article.provisions) == 1

    provision = article.provisions[0]
    assert provision.number is None
    assert provision.alineas
    assert provision.alineas[0].subdivisions == []


def test_parse_article_75b_preserves_direct_alineas_and_lists(
    french_document: StructuredLegalDocument,
) -> None:
    document = french_document
    article = next(item for item in document.articles if item.number == "75B")

    assert article.number == "75B"
    assert len(article.provisions) == 1

    provision = article.provisions[0]
    assert provision.number is None
    assert provision.alineas
    assert len(provision.alineas[0].subdivisions) > 0
    assert all(item.text for item in provision.alineas)


def test_parse_articles_with_alphabetic_identifiers(
    french_document: StructuredLegalDocument,
) -> None:
    document = french_document
    article_numbers = {article.number for article in document.articles}

    assert {"4A", "60A", "75B"}.issubset(article_numbers)


def test_parse_document_preserves_all_article_identifiers() -> None:
    from lxml import etree

    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    xml_metadata = Path("tests/fixtures/formex/ai-act-fr.doc.xml").read_bytes()
    source = SourceDocument(
        celex="02024R1689-20260727",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl(
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A02024R1689-20260727"
        ),
        retrieved_at=datetime.now(UTC),
    )

    document = EurLexParser().parse(xml_metadata, xml_content, source)

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


def test_parse_document_normalizes_all_legal_text(french_document: StructuredLegalDocument) -> None:
    document = french_document

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
            if provision.alineas:
                if provision.alineas[0].text:
                    texts.append(provision.alineas[0].text)

            texts.extend(collect_texts(provision.alineas[0].subdivisions))

    assert texts

    for text in texts:
        assert text == unicodedata.normalize("NFC", text)
        assert "\xa0" not in text
        assert "\u202f" not in text
        assert text == text.strip()
        assert not re.search(r"\s{2,}", text)


def test_parse_annexes_preserves_structure(french_document: StructuredLegalDocument) -> None:
    document = french_document

    assert len(document.annexes) == 14
    assert document.annexes[0].title.startswith("ANNEXE I")
    assert document.annexes[0].blocks

    annex_xiv = document.annexes[13]
    tables = find_blocks(annex_xiv.blocks, "TBL")

    assert len(tables) == 6
    assert all(table.attributes["COLS"] == "2" for table in tables)
    assert all(table.attributes["NO.SEQ"] for table in tables)

    rows = find_blocks(annex_xiv.blocks, "ROW")
    cells = find_blocks(annex_xiv.blocks, "CELL")

    assert len(rows) == 28
    assert len(cells) == 56

    cell_texts = [cell.text for cell in cells if cell.text]

    assert any("Code AIA" in text for text in cell_texts)
    assert any("AIP 0102" in text for text in cell_texts)


def test_parse_annex_xiv_preserves_table_hierarchy(
    french_document: StructuredLegalDocument,
) -> None:
    annex_xiv = french_document.annexes[13]
    tables = find_blocks(annex_xiv.blocks, "TBL")

    assert len(tables) == 6

    for table in tables:
        corpora = [child for child in table.children if child.element == "CORPUS"]

        assert corpora

        for corpus in corpora:
            rows = [child for child in corpus.children if child.element == "ROW"]

            assert rows

            for row in rows:
                cells = [child for child in row.children if child.element == "CELL"]

                assert len(cells) == 2


def test_parse_paragraph_preserves_multiple_alineas(
    french_document: StructuredLegalDocument,
) -> None:
    article = next(article for article in french_document.articles if article.number == "2")

    multi_alinea_provisions = [
        provision for provision in article.provisions if len(provision.alineas) > 1
    ]

    assert multi_alinea_provisions

    for provision in multi_alinea_provisions:
        assert all(alinea.text is not None or alinea.subdivisions for alinea in provision.alineas)


def test_parse_preserves_all_article_alineas(
    french_document: StructuredLegalDocument,
) -> None:
    assert len(french_document.articles) == 119

    provisions = [
        provision for article in french_document.articles for provision in article.provisions
    ]

    alineas = [alinea for provision in provisions for alinea in provision.alineas]

    assert alineas
    assert all(alinea.text is not None or alinea.subdivisions for alinea in alineas)


def test_parse_preserves_all_source_alineas(
    french_document: StructuredLegalDocument,
) -> None:
    xml_content = Path("tests/fixtures/formex/ai-act-fr.xml").read_bytes()
    root = etree.fromstring(xml_content)

    source_articles = source_articles = root.xpath(
        ".//ENACTING.TERMS//ARTICLE[not(ancestor::QUOT.S)]"
    )

    source_alineas = [
        alinea
        for article in source_articles
        for alinea in (article.findall("./PARAG/ALINEA") + article.findall("./ALINEA"))
    ]

    parsed_alineas = [
        alinea
        for article in french_document.articles
        for provision in article.provisions
        for alinea in provision.alineas
    ]

    assert len(parsed_alineas) == len(source_alineas)
    assert all(alinea.text is not None or alinea.subdivisions for alinea in parsed_alineas)


def test_parse_article_2_preserves_alinea_list_associations(
    french_document: StructuredLegalDocument,
) -> None:
    article = next(article for article in french_document.articles if article.number == "2")

    multi_alinea_provisions = [
        provision for provision in article.provisions if len(provision.alineas) > 1
    ]

    assert multi_alinea_provisions

    for provision in multi_alinea_provisions:
        for alinea in provision.alineas:
            assert alinea.text is not None or alinea.subdivisions


def find_blocks(blocks: list[LegalBlock], element: str) -> list[LegalBlock]:
    result: list[LegalBlock] = []
    for block in blocks:
        if block.element == element:
            result.append(block)
        result.extend(find_blocks(block.children, element))
    return result
