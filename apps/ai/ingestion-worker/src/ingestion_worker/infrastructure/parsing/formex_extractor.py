from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True, slots=True)
class FormexFiles:
    metadata_xml: bytes
    content_xml: bytes


class FormexExtractor:
    def extract(self, archive_content: bytes) -> FormexFiles:
        try:
            with ZipFile(BytesIO(archive_content)) as archive:
                names = archive.namelist()

                metadata_files = [name for name in names if name.lower().endswith(".doc.xml")]
                content_files = [
                    name
                    for name in archive.namelist()
                    if name.lower().endswith(".xml") and not name.lower().endswith(".doc.xml")
                ]

                if len(metadata_files) != 1:
                    raise ValueError(
                        f"Expected exactly one metadata XML file, found {len(metadata_files)}."
                    )
                if len(content_files) != 1:
                    raise ValueError(
                        f"Expected exactly one Formex XML file, found {len(content_files)}."
                    )
                metadata = archive.read(metadata_files[0])
                content = archive.read(content_files[0])

        except BadZipFile as exc:
            raise ValueError("invalid EUR-Lex ZIP archive") from exc

        if not metadata.strip():
            raise ValueError("The formex metadata XML file is empty.")
        if not content.strip():
            raise ValueError("The extracted Formex XML file is empty.")

        return FormexFiles(content_xml=content, metadata_xml=metadata)
