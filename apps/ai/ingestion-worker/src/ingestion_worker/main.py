import asyncio
from io import BytesIO
from zipfile import ZipFile

import httpx
from lxml import etree

from ingestion_worker.infrastructure.sources.eur_lex import EurLexSource


def inspect_nested_lists(content: bytes, language: str) -> None:
    with ZipFile(BytesIO(content)) as archive:
        xml_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".xml") and not name.endswith(".doc.xml")
        )
        root = etree.fromstring(archive.read(xml_name))

    article = root.xpath("//ARTICLE[@IDENTIFIER='003']")[0]

    print(f"\n=== {language.upper()} / ARTICLE 3 NESTED LISTS ===")

    nested_lists = article.xpath(".//LIST[ancestor::LIST]")

    print(f"Nested LIST count: {len(nested_lists)}")

    for nested_list in nested_lists[:5]:
        print("\n--- NESTED LIST ---")
        print(etree.tostring(nested_list, encoding="unicode")[:3000])

    print("\n=== ARTICLE 3 CONTENT COUNTS ===")

    for tag in ("PARAG", "ALINEA", "LIST", "ITEM", "TXT"):
        print(f"{tag}: {len(article.xpath(f'.//{tag}'))}")


def inspect_article_structure(content: bytes, language: str) -> None:
    with ZipFile(BytesIO(content)) as archive:
        xml_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".xml") and not name.endswith(".doc.xml")
        )
        root = etree.fromstring(archive.read(xml_name))

    article = root.xpath("//ARTICLE[@IDENTIFIER='003']")[0]

    print(f"\n=== {language.upper()} / ARTICLE 3 STRUCTURE ===")

    for element in article.iter():
        if isinstance(element.tag, str):
            text = " ".join("".join(element.itertext()).split())
            if element.tag in {
                "ARTICLE",
                "TI.ART",
                "STI.ART",
                "PARAG",
                "NO.PARAG",
                "ALINEA",
                "LIST",
                "ITEM",
                "NP",
                "NO.P",
                "TXT",
            }:
                print(
                    f"{element.tag:<12} "
                    f"depth={len(list(element.iterancestors())):<3} "
                    f"text={text[:180]!r}"
                )


def inspect_formex_xml(content: bytes, language: str) -> None:
    with ZipFile(BytesIO(content)) as archive:
        print(f"\n=== {language.upper()} FORMeX ARCHIVE ===")

        for name in archive.namelist():
            info = archive.getinfo(name)
            print(f"{name} ({info.file_size} bytes)")

        xml_names = [
            name
            for name in archive.namelist()
            if name.endswith(".xml") and not name.endswith(".doc.xml")
        ]

        if not xml_names:
            raise ValueError(f"Legal content XML not found for '{language}'.")

        xml_name = xml_names[0]
        xml_content = archive.read(xml_name).decode("utf-8")

        print(f"\n=== {language.upper()} / {xml_name} ===")
        print(xml_content[:10_000])


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        source = EurLexSource(client)

        for language in ("fr", "en"):
            content = await source.fetch_formex(language)
            print(f"{language.upper()} Formex size: {len(content)} bytes")
            print(f"Header: {content[:100]!r}")
            # inspect_formex_xml(content, language)
            inspect_nested_lists(content, language)


if __name__ == "__main__":
    asyncio.run(main())
