from uuid import NAMESPACE_URL, uuid5

from ingestion_worker.application.projection.models import LegalContentUnit, LegalContentUnitType
from ingestion_worker.domain.documents import (
    LegalAnnex,
    LegalArticle,
    LegalBlock,
    LegalDivision,
    LegalSubdivision,
    StructuredLegalDocument,
)


class LegalDocumentProjector:
    """Project structured legal documents into traceable content units."""

    def project(self, document: StructuredLegalDocument) -> list[LegalContentUnit]:
        units: list[LegalContentUnit] = []

        def visit(items: list[LegalDivision | LegalArticle], division_context: list[str]) -> None:
            for item in items:
                if isinstance(item, LegalArticle):
                    units.extend(self._project_article(document, item, division_context))
                else:
                    visit(item.children, [*division_context, item.title])

        visit(document.body, [])

        for annex_index, annex in enumerate(document.annexes, start=1):
            units.extend(self._project_annex(document, annex, annex_index))

        if document.final is not None:
            units.append(self._project_final(document, document.final))

        return units

    def _project_article(
        self,
        document: StructuredLegalDocument,
        article: LegalArticle,
        division_context: list[str],
    ) -> list[LegalContentUnit]:
        article_context = self._build_article_context(
            article.number,
            article.title,
            division_context,
        )
        units: list[LegalContentUnit] = []

        for provision in article.provisions:
            for alinea_index, alinea in enumerate(provision.alineas, start=1):
                alinea_context = self._join_text(article_context, provision.number, alinea.text)

                if not alinea.subdivisions:
                    if alinea_context:
                        units.append(
                            self._create_unit(
                                document=document,
                                content=alinea_context,
                                unit_type="article",
                                article_number=article.number,
                                paragraph_number=provision.number,
                                alinea_index=alinea_index,
                            )
                        )
                    continue

                for index, subdivision in enumerate(alinea.subdivisions, start=1):
                    units.extend(
                        self._project_subdivision(
                            document=document,
                            article_number=article.number,
                            paragraph_number=provision.number,
                            alinea_index=alinea_index,
                            article_context=alinea_context,
                            subdivision=subdivision,
                            parent_texts=[],
                            parent_path=[],
                            sibling_index=index,
                        )
                    )

        return units

    def _project_subdivision(
        self,
        document: StructuredLegalDocument,
        article_number: str,
        paragraph_number: str | None,
        alinea_index: int,
        article_context: str,
        subdivision: LegalSubdivision,
        parent_texts: list[str],
        parent_path: list[str],
        sibling_index: int,
    ) -> list[LegalContentUnit]:
        number = subdivision.number or f"item-{sibling_index}"
        current_path = [*parent_path, number]

        subdivision_context = self._join_text(subdivision.number, subdivision.text)
        current_texts = (
            [*parent_texts, subdivision_context] if subdivision_context else parent_texts
        )

        content = self._join_text(article_context, *current_texts)
        units: list[LegalContentUnit] = []

        if subdivision.text and content:
            units.append(
                self._create_unit(
                    document=document,
                    content=content,
                    unit_type="subdivision",
                    article_number=article_number,
                    paragraph_number=paragraph_number,
                    alinea_index=alinea_index,
                    subdivision_path=current_path,
                )
            )

        for index, child in enumerate(subdivision.children, start=1):
            units.extend(
                self._project_subdivision(
                    document=document,
                    article_number=article_number,
                    paragraph_number=paragraph_number,
                    alinea_index=alinea_index,
                    article_context=article_context,
                    subdivision=child,
                    parent_texts=current_texts,
                    parent_path=current_path,
                    sibling_index=index,
                )
            )

        return units

    def _project_annex(
        self,
        document: StructuredLegalDocument,
        annex: LegalAnnex,
        annex_index: int,
    ) -> list[LegalContentUnit]:
        units: list[LegalContentUnit] = []
        annex_context = f"Annexe - {annex.title}"

        for index, block in enumerate(annex.blocks, start=1):
            units.extend(
                self._project_annex_block(
                    document=document,
                    annex=annex,
                    annex_index=annex_index,
                    block=block,
                    parent_texts=[],
                    parent_path=[],
                    sibling_index=index,
                    annex_context=annex_context,
                )
            )

        return units

    def _project_annex_block(
        self,
        document: StructuredLegalDocument,
        annex: LegalAnnex,
        annex_index: int,
        block: LegalBlock,
        parent_texts: list[str],
        parent_path: list[str],
        sibling_index: int,
        annex_context: str,
        table_attributes: dict[str, str] | None = None,
    ) -> list[LegalContentUnit]:
        segment = block.number or f"{block.element}[{sibling_index}]"
        current_path = [*parent_path, f"{block.element}:{segment}"]

        block_context = self._join_text(block.number, block.text)
        current_texts = [*parent_texts, block_context] if block_context else [*parent_texts]

        current_table_attributes = block.attributes if block.element == "TBL" else table_attributes

        if block.element == "ROW":
            return [
                self._project_annex_table_row(
                    document=document,
                    annex=annex,
                    annex_index=annex_index,
                    row=block,
                    row_path=current_path,
                    row_index=sibling_index,
                    parent_texts=parent_texts,
                    table_attributes=current_table_attributes or {},
                    annex_context=annex_context,
                )
            ]

        content = self._join_text(annex_context, *current_texts)
        units: list[LegalContentUnit] = []

        if block.text and content:
            path = " > ".join(current_path)
            unit_id = str(
                uuid5(
                    NAMESPACE_URL,
                    ":".join(
                        [
                            document.celex,
                            document.language,
                            document.consolidation_date.isoformat(),
                            "annex",
                            str(annex_index),
                            path,
                        ]
                    ),
                )
            )

            units.append(
                LegalContentUnit(
                    id=unit_id,
                    type="annex_block",
                    content=content,
                    annex_title=annex.title,
                    language=document.language,
                    celex=document.celex,
                    consolidation_date=document.consolidation_date,
                    source_url=document.source_url,
                    metadata={
                        "block_path": path,
                        "element": block.element,
                    },
                )
            )

        child_parent_texts = current_texts

        if block.element == "GR.SEQ":
            title = next(
                (child for child in block.children if child.element == "TITLE"),
                None,
            )

            if title is not None:
                title_context = self._flatten_block_text(title)

                if title_context:
                    child_parent_texts = [
                        *current_texts,
                        title_context,
                    ]

        for index, child in enumerate(block.children, start=1):
            child_context = current_texts

            if block.element == "GR.SEQ" and child.element != "TITLE":
                child_context = child_parent_texts

            units.extend(
                self._project_annex_block(
                    document=document,
                    annex=annex,
                    annex_index=annex_index,
                    block=child,
                    parent_texts=child_context,
                    parent_path=current_path,
                    sibling_index=index,
                    annex_context=annex_context,
                    table_attributes=current_table_attributes,
                )
            )

        return units

    def _create_unit(
        self,
        document: StructuredLegalDocument,
        content: str,
        unit_type: LegalContentUnitType,
        article_number: str,
        paragraph_number: str | None,
        alinea_index: int,
        subdivision_path: list[str] | None = None,
    ) -> LegalContentUnit:
        path = subdivision_path or []

        id_parts = [
            document.celex,
            document.language,
            document.consolidation_date.isoformat(),
            "article",
            article_number,
            "paragraph",
            paragraph_number or "none",
            "alinea",
            str(alinea_index),
            "type",
            unit_type,
            *path,
        ]

        unit_id = str(uuid5(NAMESPACE_URL, ":".join(id_parts)))

        return LegalContentUnit(
            id=unit_id,
            type=unit_type,
            content=content,
            article_number=article_number,
            paragraph_number=paragraph_number,
            alinea_index=alinea_index,
            subdivision_path=path,
            language=document.language,
            celex=document.celex,
            consolidation_date=document.consolidation_date,
            source_url=document.source_url,
        )

    def _project_final(
        self,
        document: StructuredLegalDocument,
        final: LegalBlock,
    ) -> LegalContentUnit:
        content = self._flatten_block_text(final)

        unit_id = str(
            uuid5(
                NAMESPACE_URL,
                ":".join(
                    [
                        document.celex,
                        document.language,
                        document.consolidation_date.isoformat(),
                        "final",
                    ]
                ),
            )
        )

        return LegalContentUnit(
            id=unit_id,
            type="final",
            content=content,
            language=document.language,
            celex=document.celex,
            consolidation_date=document.consolidation_date,
            source_url=document.source_url,
            metadata={
                "element": "FINAL",
                "block_path": "FINAL",
            },
        )

    def _build_article_context(
        self,
        number: str,
        title: str | None,
        division_context: list[str],
    ) -> str:
        parts = [*division_context, f"Article {number}"]

        if title:
            parts[-1] = f"{parts[-1]} - {title}"

        return self._join_text(*parts)

    def _project_annex_table_row(
        self,
        document: StructuredLegalDocument,
        annex: LegalAnnex,
        annex_index: int,
        row: LegalBlock,
        row_path: list[str],
        row_index: int,
        parent_texts: list[str],
        table_attributes: dict[str, str],
        annex_context: str,
    ) -> LegalContentUnit:
        cells = sorted(
            [child for child in row.children if child.element == "CELL"],
            key=lambda cell: int(cell.attributes.get("COL", "0")),
        )

        cell_values = [self._flatten_block_text(cell) for cell in cells]

        row_content = " | ".join(cell_values)
        content = self._join_text(
            annex_context,
            *parent_texts,
            row_content,
        )

        path = " > ".join(row_path)

        unit_id = str(
            uuid5(
                NAMESPACE_URL,
                ":".join(
                    [
                        document.celex,
                        document.language,
                        document.consolidation_date.isoformat(),
                        "annex",
                        str(annex_index),
                        path,
                    ]
                ),
            )
        )

        return LegalContentUnit(
            id=unit_id,
            type="table_row",
            content=content,
            annex_title=annex.title,
            language=document.language,
            celex=document.celex,
            consolidation_date=document.consolidation_date,
            source_url=document.source_url,
            metadata={
                "block_path": path,
                "element": "ROW",
                "table_index": table_attributes.get("NO.SEQ", ""),
                "row_index": str(row_index),
                "row_type": row.attributes.get("TYPE", ""),
                "table_cols": table_attributes.get("COLS", ""),
                "cell_count": str(len(cells)),
            },
        )

    def _block_context_text(self, block: LegalBlock) -> str:
        return self._join_text(block.number, block.text)

    def _flatten_block_text(self, block: LegalBlock) -> str:
        parts = [block.number, block.text]

        for child in block.children:
            parts.append(self._flatten_block_text(child))

        return self._join_text(*parts)

    @staticmethod
    def _join_text(*parts: str | None) -> str:
        return " ".join(part.strip() for part in parts if part and part.strip())
