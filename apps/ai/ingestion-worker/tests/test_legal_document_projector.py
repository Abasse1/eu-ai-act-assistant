
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import HttpUrl

from ingestion_worker.domain.documents import (
    LegalAnnex,
    LegalArticle,
    LegalAlinea,
    LegalBlock,
    LegalDivision,
    LegalProvision,
    LegalSubdivision,
    StructuredLegalDocument,
)

from ingestion_worker.application.projection.legal_document_projector import LegalDocumentProjector
from ingestion_worker.domain.documents import SourceDocument, StructuredLegalDocument
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser


@pytest.fixture
def french_document() -> StructuredLegalDocument:
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


@pytest.fixture
def projector() -> LegalDocumentProjector:
    return LegalDocumentProjector()


def test_project_creates_traceable_units(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    assert units
    assert all(unit.content.strip() for unit in units)
    article_units = [
    unit for unit in units
    if unit.type in ("article", "subdivision")
    ]

    annex_units = [
        unit for unit in units
        if unit.type == "annex_block"
    ]
    
    assert article_units
    assert all(unit.article_number for unit in article_units)
    
    assert annex_units
    assert all(unit.annex_title for unit in annex_units)
    assert all(unit.metadata.get("block_path") for unit in annex_units)
    assert all(unit.celex == french_document.celex for unit in units)
    assert all(unit.language == french_document.language for unit in units)
    assert all(unit.consolidation_date == french_document.consolidation_date for unit in units)
    assert all(unit.source_url == french_document.source_url for unit in units)
    assert all(
    unit.type in {"article", "subdivision", "annex_block", "table_row","final"}
    for unit in units
    )
    assert len({unit.id for unit in units}) == len(units)


def test_project_preserves_nested_subdivision_context(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    nested_units = [
        unit
        for unit in units
        if unit.type == "subdivision" and len(unit.subdivision_path) > 1
    ]

    assert nested_units
    assert all(unit.content.strip() for unit in nested_units)
    assert all(len(unit.subdivision_path) > 1 for unit in nested_units)


def test_project_preserves_subdivision_paths(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    subdivision_units = [unit for unit in units if unit.type == "subdivision"]

    assert subdivision_units
    assert all(unit.subdivision_path for unit in subdivision_units)
    assert any(len(unit.subdivision_path) > 1 for unit in subdivision_units)


def test_article_units_have_no_subdivision_path(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    article_units = [unit for unit in units if unit.type == "article"]

    assert article_units
    assert all(not unit.subdivision_path for unit in article_units)


def test_project_generates_stable_ids(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    first_projection = projector.project(french_document)
    second_projection = projector.project(french_document)

    assert [unit.id for unit in first_projection] == [unit.id for unit in second_projection]


def test_projected_unit_ids_are_unique(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    ids = [unit.id for unit in units]

    assert len(ids) == len(set(ids))


def test_project_generates_different_ids_for_different_consolidation_dates(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    original_units = projector.project(french_document)

    updated_document = french_document.model_copy(
        update={"consolidation_date": date(2026, 8, 1)}
    )
    updated_units = projector.project(updated_document)

    assert len(original_units) == len(updated_units)
    assert {unit.id for unit in original_units}.isdisjoint(
        {unit.id for unit in updated_units}
    )


def test_project_preserves_article_3(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    article_3_units = [
        unit for unit in units
        if unit.article_number == "3"
    ]

    assert article_3_units
    assert all("Article 3" in unit.content for unit in article_3_units)
    assert all(unit.celex == french_document.celex for unit in article_3_units)

    numbered_units = [unit for unit in article_3_units if unit.subdivision_path]
    assert numbered_units



def test_project_includes_parent_division_context(
    projector: LegalDocumentProjector,
) -> None:
    document = StructuredLegalDocument(
        celex="02024R1689",
        title="Artificial Intelligence Act",
        document_type="regulation",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl("https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689"),
        retrieved_at=datetime.now(UTC),
        body=[
            LegalDivision(
                title="Titre III - Systèmes à haut risque",
                level=1,
                children=[
                    LegalDivision(
                        title="Chapitre II - Exigences",
                        level=2,
                        children=[
                            LegalArticle(
                                number="15",
                                title="Exactitude, robustesse et cybersécurité",
                                provisions=[
                                    LegalProvision(
                                        number="1",
                                        alineas=[
                                            LegalAlinea(
                                                text="Les systèmes doivent satisfaire aux exigences suivantes.",
                                                subdivisions=[
                                                    LegalSubdivision(
                                                        number="a",
                                                        text="Maintenir un niveau approprié de précision.",
                                                    )
                                                ],
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    units = projector.project(document)

    assert len(units) == 1

    content = units[0].content

    assert "Titre III - Systèmes à haut risque" in content
    assert "Chapitre II - Exigences" in content
    assert "Article 15" in content
    assert "Exactitude, robustesse et cybersécurité" in content


def test_project_includes_parent_subdivision_text(
    projector: LegalDocumentProjector,
) -> None:
    document = StructuredLegalDocument(
        celex="02024R1689",
        title="Artificial Intelligence Act",
        document_type="regulation",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl("https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689"),
        retrieved_at=datetime.now(UTC),
        body=[
            LegalArticle(
                number="5",
                title="Pratiques interdites",
                provisions=[
                    LegalProvision(
                        number="1",
                        alineas=[
                            LegalAlinea(
                                text="Les pratiques suivantes sont interdites.",
                                subdivisions=[
                                    LegalSubdivision(
                                        number="a",
                                        text="Première catégorie de pratiques.",
                                        children=[
                                            LegalSubdivision(
                                                number="i",
                                                text="Première pratique spécifique.",
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    units = projector.project(document)

    nested_unit = next(
        unit
        for unit in units
        if unit.subdivision_path == ["a", "i"]
    )

    assert "Les pratiques suivantes sont interdites." in nested_unit.content
    assert "Première catégorie de pratiques." in nested_unit.content
    assert "Première pratique spécifique." in nested_unit.content


def test_project_preserves_annex_blocks(
    projector: LegalDocumentProjector,
) -> None:
    document = StructuredLegalDocument(
        celex="02024R1689",
        title="Artificial Intelligence Act",
        document_type="regulation",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl("https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689"),
        retrieved_at=datetime.now(UTC),
        annexes=[
            LegalAnnex(
                title="ANNEXE III - Systèmes d'IA à haut risque",
                blocks=[
                    LegalBlock(
                        element="P",
                        text="Les systèmes d'IA visés à l'article 6 sont notamment les suivants.",
                        children=[
                            LegalBlock(
                                element="LIST",
                                children=[
                                    LegalBlock(
                                        element="ITEM",
                                        number="1",
                                        text="Biométrie.",
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    units = projector.project(document)

    annex_units = [unit for unit in units if unit.type == "annex_block"]

    assert len(annex_units) == 2
    assert all(unit.annex_title == "ANNEXE III - Systèmes d'IA à haut risque" for unit in annex_units)
    assert all(unit.celex == document.celex for unit in annex_units)
    assert all(unit.consolidation_date == document.consolidation_date for unit in annex_units)

    item_unit = next(unit for unit in annex_units if "ITEM:1" in unit.metadata["block_path"])

    assert "Les systèmes d'IA visés à l'article 6" in item_unit.content
    parent_unit = next(
    unit for unit in annex_units
    if unit.metadata["element"] == "P"
    )

    item_unit = next(
        unit for unit in annex_units
        if unit.metadata["element"] == "ITEM"
    )

    assert "sont notamment les suivants" in parent_unit.content
    assert "Biométrie." in item_unit.content

    assert item_unit.metadata["block_path"] == (
        "P:P[1] > LIST:LIST[1] > ITEM:1"
    )

    assert "sont notamment les suivants" in item_unit.content


def test_project_generates_stable_annex_block_ids(
    projector: LegalDocumentProjector,
) -> None:
    document = StructuredLegalDocument(
        celex="02024R1689",
        title="Artificial Intelligence Act",
        document_type="regulation",
        language="fr",
        consolidation_date=date(2026, 7, 27),
        source_url=HttpUrl("https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689"),
        retrieved_at=datetime.now(UTC),
        annexes=[
            LegalAnnex(
                title="ANNEXE III",
                blocks=[
                    LegalBlock(
                        element="P",
                        number="1",
                        text="Contenu de test.",
                    )
                ],
            )
        ],
    )

    first_projection = projector.project(document)
    second_projection = projector.project(document)

    first_ids = [unit.id for unit in first_projection]
    second_ids = [unit.id for unit in second_projection]

    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids))

def test_project_annex_includes_np_number(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    annex = next(
        annex for annex in french_document.annexes
        if annex.title.startswith("ANNEXE III ")
    )

    annex_units = [
        unit for unit in units
        if unit.type == "annex_block"
        and unit.annex_title == annex.title
    ]

    assert any(
        "1. Biométrie" in unit.content
        for unit in annex_units
    )

def test_project_annex_includes_section_title_context(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == "ANNEXE XIV"
    ]

    assert table_units

    first_data_row = next(
        unit for unit in table_units
        if "AIP 0102" in unit.content
    )

    assert "2." in first_data_row.content
    assert "Systèmes d'IA relevant de l'annexe I" in first_data_row.content

def test_project_annex_tables_as_rows(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == "ANNEXE XIV"
    ]

    assert len(table_units) == 28

def test_project_annex_does_not_create_cell_units(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    assert not any(
        unit.type == "annex_block"
        and unit.metadata.get("element") == "CELL"
        for unit in units
    )

def test_project_annex_table_row_preserves_group_context(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    annex = next(
        annex for annex in french_document.annexes
        if annex.title.startswith("ANNEXE XIV")
    )

    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == annex.title
    ]

    assert table_units

    expected_contexts = (
        "Liste des codes, des catégories et des systèmes d'IA correspondants",
        "Systèmes d'IA relevant de l'annexe I",
    )

    assert any(
        all(context in unit.content for context in expected_contexts)
        for unit in table_units
    )

def test_project_annex_tables_preserves_all_rows(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    annex = next(
        annex for annex in french_document.annexes
        if annex.title.startswith("ANNEXE XIV")
    )

    def count_elements(blocks: list[LegalBlock], element: str) -> int:
        return sum(
            (1 if block.element == element else 0)
            + count_elements(block.children, element)
            for block in blocks
        )

    expected_rows = count_elements(annex.blocks, "ROW")

    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == annex.title
    ]

    assert len(table_units) == expected_rows
    assert len({unit.id for unit in table_units}) == len(table_units)


def test_project_annex_table_rows_preserves_cells(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    annex = next(
        annex for annex in french_document.annexes
        if annex.title.startswith("ANNEXE XIV")
    )

    def flatten(block: LegalBlock) -> str:
        parts = [block.text] if block.text else []
        parts.extend(flatten(child) for child in block.children)
        return " ".join(part.strip() for part in parts if part and part.strip())

    def find_rows(blocks: list[LegalBlock]) -> list[LegalBlock]:
        rows: list[LegalBlock] = []
        for block in blocks:
            if block.element == "ROW":
                rows.append(block)
            rows.extend(find_rows(block.children))
        return rows

    source_rows = find_rows(annex.blocks)
    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == annex.title
    ]

    # Every source row must retain its two cells.
    assert len(table_units) == len(source_rows)
    assert all(unit.metadata["cell_count"] == "2" for unit in table_units)

    # At least one source row contains an empty second cell.
    empty_second_cell_rows = [
        row for row in source_rows
        if len([c for c in row.children if c.element == "CELL"]) == 2
        and flatten([c for c in row.children if c.element == "CELL"][0])
        and not flatten([c for c in row.children if c.element == "CELL"][1])
    ]

    assert empty_second_cell_rows

    # The empty second cell must remain visible through the separator.
    assert any(
        unit.content.rstrip().endswith("|")
        for unit in table_units
    )


def test_project_annex_table_rows_preserves_metadata(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    annex = next(
        annex for annex in french_document.annexes
        if annex.title.startswith("ANNEXE XIV")
    )

    units = projector.project(french_document)

    table_units = [
        unit for unit in units
        if unit.type == "table_row"
        and unit.annex_title == annex.title
    ]

    assert table_units

    for unit in table_units:
        metadata = unit.metadata

        assert metadata["element"] == "ROW"
        assert metadata["block_path"]
        assert metadata["table_index"]
        assert metadata["row_index"].isdigit()
        assert metadata["table_cols"] == "2"
        assert metadata["cell_count"] == "2"
        assert "row_type" in metadata


from collections import Counter

def test_project_document_coverage_report(
    french_document: StructuredLegalDocument,
    projector: LegalDocumentProjector,
) -> None:
    units = projector.project(french_document)

    counts = Counter(unit.type for unit in units)

    projected_articles = {
        unit.article_number
        for unit in units
        if unit.article_number
    }

    projected_annexes = {
        unit.annex_title
        for unit in units
        if unit.annex_title
    }

    expected_annexes = {
        annex.title for annex in french_document.annexes
    }

    missing_annexes = expected_annexes - projected_annexes

    print("\n=== DOCUMENT PROJECTION REPORT ===")
    print(f"Source articles       : {len(french_document.articles)}")
    print(f"Source annexes        : {len(french_document.annexes)}")
    print(f"Projected units       : {len(units)}")
    print(f"Article units         : {counts['article']}")
    print(f"Subdivision units     : {counts['subdivision']}")
    print(f"Annex block units     : {counts['annex_block']}")
    print(f"Table row units       : {counts['table_row']}")
    print(f"Distinct articles     : {len(projected_articles)}")
    print(f"Distinct annexes      : {len(projected_annexes)}")
    print(f"Missing annexes       : {sorted(missing_annexes)}")

    assert units
    assert not missing_annexes

    print("\n=== FINAL SECTION ===")

    if french_document.final:
               inspect_block(french_document.final)


def inspect_block(block: LegalBlock, depth: int = 0) -> None:
    indent = "  " * depth
    print(
        f"{indent}{block.element}: "
        f"number={block.number!r}, "
        f"text={block.text!r}, "
        f"attributes={block.attributes}"
    )

    for child in block.children:
        inspect_block(child, depth + 1)


   