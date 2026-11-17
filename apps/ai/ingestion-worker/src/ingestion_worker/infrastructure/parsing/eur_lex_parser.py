import unicodedata
from typing import Any

from lxml import etree
from lxml.etree import ElementBase

from ingestion_worker.domain.documents import (
    LegalAlinea,
    LegalAnnex,
    LegalArticle,
    LegalBlock,
    LegalDivision,
    LegalProvision,
    LegalSubdivision,
    SourceDocument,
    StructuredLegalDocument,
)
from ingestion_worker.infrastructure.parsing.formex_blocks import FormexBlockParser

XmlElement = Any


class EurLexParser:
    def __init__(self) -> None:
        self._formex_block_parser = FormexBlockParser()

    def parse(
        self, xml_metadata: bytes, xml_content: bytes, document: SourceDocument
    ) -> StructuredLegalDocument:
        metadata_root = self._parse_xml(xml_metadata)
        root = self._parse_xml(xml_content)

        cons_doc = root.find("./CONS.DOC")

        if cons_doc is None:
            raise ValueError("Document is missing its CONS.DOC element.")

        annexes = self._parse_annexes(cons_doc)
        final = self._parse_final(cons_doc)

        title_element = metadata_root.find("./PAPER/VOLUME.PAPER/ITEM.VOLUME/TITLE/TI/P")

        if title_element is None:
            raise ValueError("Document metadata is missing its official title.")

        title = self._extract_metadata_title(title_element)
        legal_value = metadata_root.findtext("./FMX/DOC.MAIN.PUB/LEGAL.VALUE")
        document_type = self._parse_document_type(legal_value)

        enacting_terms = root.find(".//ENACTING.TERMS")

        if enacting_terms is None:
            raise ValueError("Document is missing its ENACTING.TERMS element.")

        body = self._parse_body_items(enacting_terms)

        articles = self._collect_articles(body)

        if not articles:
            raise ValueError("No legal articles found in the Formex document.")

        return StructuredLegalDocument(
            celex=document.celex,
            title=title,
            document_type=document_type,
            language=document.language,
            consolidation_date=document.consolidation_date,
            source_url=document.source_url,
            body=body,
            retrieved_at=document.retrieved_at,
            final=final,
            annexes=annexes,
        )

    def _parse_article(self, element: XmlElement) -> LegalArticle:
        identifier = element.get("IDENTIFIER")
        if not identifier:
            raise ValueError("Article is missing its IDENTIFIER.")

        number = identifier.lstrip("0")
        if not number:
            raise ValueError(f"Invalid article identifier: {identifier}")

        title = self._direct_text(element, "STI.ART")

        provisions: list[LegalProvision] = []

        for paragraph in element.findall("./PARAG"):
            provisions.append(self._parse_paragraph(paragraph))

        direct_alineas = element.findall("./ALINEA")
        if direct_alineas:
            provisions.append(
                self._parse_provision_content(
                    number=None,
                    alinea_elements=direct_alineas,
                )
            )

        return LegalArticle(
            number=number,
            title=title,
            provisions=provisions,
        )

    def _parse_paragraph(self, element: XmlElement) -> LegalProvision:
        number = self._direct_text(element, "NO.PARAG")
        alinea_elements = element.findall("./ALINEA")

        if not alinea_elements:
            raise ValueError(f"Paragraph '{number}' has no ALINEA elements.")

        return self._parse_provision_content(
            number=number,
            alinea_elements=alinea_elements,
        )

    def _parse_provision_content(
        self, number: str | None, alinea_elements: list[ElementBase]
    ) -> LegalProvision:
        alineas: list[LegalAlinea] = []

        for alinea in alinea_elements:
            text = self._extract_text(alinea) or None
            subdivisions: list[LegalSubdivision] = []

            for list_element in self._find_lists(alinea):
                subdivisions.extend(self._parse_list(list_element))

            alineas.append(
                LegalAlinea(
                    text=text,
                    subdivisions=subdivisions,
                )
            )

        return LegalProvision(number=number, alineas=alineas)

    def _find_lists(self, element: ElementBase) -> list[ElementBase]:
        """Find the first level of lists below an element."""

        result: list[ElementBase] = []

        def visit(parent: ElementBase) -> None:
            for child in parent:
                if child.tag == "LIST":
                    result.append(child)
                else:
                    visit(child)

        visit(element)
        return result

    def _extract_text(self, element: ElementBase) -> str:
        parts: list[str] = []

        def visit(node: ElementBase) -> None:
            if node.text:
                parts.append(node.text)

            for child in node:
                if child.tag not in {"LIST", "NO.P", "NO.PARAG"}:
                    visit(child)

                if child.tail:
                    parts.append(child.tail)

        visit(element)

        return self._clean_text("".join(parts))

    def _direct_text(self, element: XmlElement, path: str) -> str | None:
        child = element.find(f"./{path}")

        if child is None:
            return None

        return self._clean_text("".join(child.itertext())) or None

    def _parse_list(self, element: ElementBase) -> list[LegalSubdivision]:
        subdivisions: list[LegalSubdivision] = []
        list_type = element.get("TYPE")

        for item in element.findall("./ITEM"):
            number = self._direct_text(item, "NP/NO.P")
            text = self._extract_text(item)

            nested_subdivisions: list[LegalSubdivision] = []

            for nested_list in self._find_lists(item):
                nested_subdivisions.extend(self._parse_list(nested_list))

            if not text:
                if nested_subdivisions:
                    raise ValueError(f"List item '{number}' contains nested lists but no text.")
                raise ValueError(f"List item '{number}' has no extractable text.")

            subdivisions.append(
                LegalSubdivision(
                    number=number, children=nested_subdivisions, text=text, list_type=list_type
                )
            )
        return subdivisions

    def _parse_alinea(self, element: ElementBase) -> LegalProvision:
        return self._parse_provision_content(number=None, alinea_elements=[element])

    def _extract_metadata_title(self, element: XmlElement) -> str:
        parts: list[str] = []

        def visit(node: ElementBase) -> None:
            if node.text:
                parts.append(node.text)

            for child in node:
                if child.tag != "NOTE":
                    visit(child)
                if child.tail:
                    parts.append(child.tail)

        visit(element)
        return self._clean_text("".join(parts))

    def _parse_body_items(
        self, parent: XmlElement, level: int = 1
    ) -> list[LegalDivision | LegalArticle]:
        items: list[LegalDivision | LegalArticle] = []

        for child in parent:
            if child.tag == "DIVISION":
                items.append(self._parse_division(child, level))
            elif child.tag == "ARTICLE":
                items.append(self._parse_article(child))

        return items

    def _parse_division(self, element: ElementBase, level: int) -> LegalDivision:
        title_element = element.find("./TITLE")

        if title_element is None:
            raise ValueError("Legal division is missing its TITLE element.")

        title_paragraphs = title_element.xpath(".//P")

        if title_paragraphs:
            title = self._clean_text(
                " ".join("".join(paragraph.itertext()) for paragraph in title_paragraphs)
            )
        else:
            title = self._clean_text(" ".join(title_element.itertext()))

        if not title:
            raise ValueError("Legal division contains an empty title.")

        return LegalDivision(
            title=title,
            level=level,
            children=self._parse_body_items(element, level + 1),
        )

    def _collect_articles(self, items: list[LegalDivision | LegalArticle]) -> list[LegalArticle]:
        articles: list[LegalArticle] = []

        for item in items:
            if isinstance(item, LegalArticle):
                articles.append(item)
            else:
                articles.extend(self._collect_articles(item.children))

        return articles

    def _parse_annexes(self, cons_doc: XmlElement) -> list[LegalAnnex]:
        annex_elements = cons_doc.findall("./CONS.ANNEX")
        annexes: list[LegalAnnex] = []

        for element in annex_elements:
            title_element = element.find("./TITLE")

            if title_element is None:
                raise ValueError("Legal annex is missing its TITLE element.")

            title = self._extract_annex_title(title_element)
            contents = element.find("./CONTENTS")

            if contents is None:
                raise ValueError(f"Legal annex '{title}' is missing its CONTENTS element.")

            blocks = [
                self._formex_block_parser.parse(child)
                for child in contents
                if isinstance(child.tag, str)
            ]

            annexes.append(
                LegalAnnex(
                    title=title,
                    blocks=blocks,
                )
            )

        return annexes

    def _extract_annex_title(self, element: XmlElement) -> str:
        paragraphs = element.xpath("./TI/P | ./STI/P")

        if paragraphs:
            return self._clean_text(
                " ".join("".join(paragraph.itertext()) for paragraph in paragraphs)
            )

        return self._clean_text(" ".join(element.itertext()))

    def _parse_final(self, cons_doc: XmlElement) -> LegalBlock | None:
        element = cons_doc.find("./FINAL")

        if element is None:
            return None

        return self._formex_block_parser.parse(element)

    @staticmethod
    def _clean_text(text: str) -> str:
        normalized = unicodedata.normalize("NFC", text)
        normalized = normalized.replace("\xa0", " ").replace("\u202f", " ")
        return " ".join(normalized.split())

    @staticmethod
    def _parse_document_type(legal_value: str | None) -> str:
        document_types = {"REG": "regulation"}

        if legal_value is None or legal_value not in document_types:
            raise ValueError(f"Unsupported or missing EUR-Lex legal value: {legal_value}")

        return document_types[legal_value]

    @staticmethod
    def _parse_xml(content: bytes) -> XmlElement:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            recover=False,
            huge_tree=False,
        )
        return etree.fromstring(content, parser=parser)
