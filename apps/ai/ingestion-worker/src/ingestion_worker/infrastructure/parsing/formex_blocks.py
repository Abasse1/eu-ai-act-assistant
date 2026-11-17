import unicodedata
from typing import Any

from ingestion_worker.domain.documents import LegalBlock

XmlElement = Any


class FormexBlockParser:
    """Parse generic Formex XML elements into legal document blocks."""

    BLOCK_ELEMENTS = {
        "TITLE",
        "TI",
        "STI",
        "P",
        "GR.SEQ",
        "NP",
        "TXT",
        "LIST",
        "ITEM",
        "FT",
        "HT",
        "TBL",
        "CORPUS",
        "ROW",
        "CELL",
        "IE",
    }

    def parse(self, element: XmlElement) -> LegalBlock:
        number = None

        if element.tag == "NP":
            number = self._direct_text(element, "NO.P")

        children: list[LegalBlock] = []
        text_parts: list[str] = []

        if element.text:
            text_parts.append(element.text)

        for child in element:
            if not isinstance(child.tag, str):
                if child.tail:
                    text_parts.append(child.tail)
                continue

            if child.tag == "NO.P" and element.tag == "NP":
                if child.tail:
                    text_parts.append(child.tail)
                continue

            if child.tag in self.BLOCK_ELEMENTS:
                children.append(self.parse(child))
            else:
                text_parts.append(self._extract_inline_text(child))

            if child.tail:
                text_parts.append(child.tail)

        return LegalBlock(
            element=element.tag,
            number=number,
            text=self._clean_text("".join(text_parts)) or None,
            attributes=dict(element.attrib),
            children=children,
        )

    def _direct_text(self, element: XmlElement, path: str) -> str | None:
        child = element.find(f"./{path}")
        if child is None:
            return None
        return self._clean_text("".join(child.itertext())) or None

    def _extract_inline_text(self, element: XmlElement) -> str:
        parts: list[str] = []

        if element.text:
            parts.append(element.text)

        for child in element:
            if isinstance(child.tag, str):
                parts.append(self._extract_inline_text(child))
            if child.tail:
                parts.append(child.tail)

        return "".join(parts)

    @staticmethod
    def _clean_text(text: str) -> str:
        normalized = unicodedata.normalize("NFC", text)
        normalized = normalized.replace("\xa0", " ").replace("\u202f", " ")
        return " ".join(normalized.split())
