import unicodedata
from typing import Any

from lxml import etree
from lxml.etree import ElementBase

from ingestion_worker.domain.documents import (
    LegalArticle,
    LegalProvision,
    LegalSubdivision,
    SourceDocument,
    StructuredLegalDocument,
)

XmlElement = Any

class EurLexParser:
    def parse(self, xml_content: bytes, document: SourceDocument) -> StructuredLegalDocument:
        root = etree.fromstring(xml_content)

        article_elements = root.xpath(".//ENACTING.TERMS//ARTICLE")

        articles = [self._parse_article(element) for element in article_elements]

        if not articles:
            raise ValueError("No legal artuicles found in the Formex document.")

        return StructuredLegalDocument(
            celex=document.celex,
            language=document.language,
            consolidation_date=document.consolidation_date,
            source_url=document.source_url,
            articles=articles,
            retrieved_at=document.retrieved_at,
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
        texts: list[str] = []
        subdivisions: list[LegalSubdivision] = []

        for alinea in alinea_elements:
            text: str = self._extract_text(alinea)
            if text:
                texts.append(text)
            for list_element in self._find_lists(alinea):
                subdivisions.extend(self._parse_list(list_element))
        return LegalProvision(
            number=number, text=" ".join(texts) or None, subdivisions=subdivisions
        )

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

    @staticmethod
    def _clean_text(text: str) -> str:
        normalized = unicodedata.normalize("NFC", text)
        normalized = normalized.replace("\xa0", " ").replace("\u202f", " ")
        return " ".join(normalized.split())
