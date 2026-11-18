from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True, slots=True)
class FormexFiles:
    metadata_xml: bytes
    content_xml: bytes


class FormexExtractor:
    def __init__(self, max_uncompressed_size: int = 50 * 1024 * 1024) -> None:
        if max_uncompressed_size <= 0:
            raise ValueError("Maximum uncompressed size must be greater than zero")

        self._max_uncompressed_size = max_uncompressed_size

    def extract(self, archive_content: bytes) -> FormexFiles:
        try:
            with ZipFile(BytesIO(archive_content)) as archive:
                names = archive.namelist()

                metadata_files = [name for name in names if name.lower().endswith(".doc.xml")]
                content_files = [
                    name
                    for name in names
                    if name.lower().endswith(".xml") and not name.lower().endswith(".doc.xml")
                ]

                if len(metadata_files) != 1:
                    raise ValueError(
                        f"Expected exactly one metadata XML file, found {len(metadata_files)}"
                    )

                if len(content_files) != 1:
                    raise ValueError(
                        f"Expected exactly one Formex XML file, found {len(content_files)}"
                    )

                selected_files = [metadata_files[0], content_files[0]]

                uncompressed_size = sum(archive.getinfo(name).file_size for name in selected_files)

                if uncompressed_size > self._max_uncompressed_size:
                    raise ValueError(
                        f"Uncompressed XML files exceed the maximum allowed size "
                        f"of {self._max_uncompressed_size} bytes"
                    )

                metadata = archive.read(metadata_files[0])
                content = archive.read(content_files[0])

        except BadZipFile as exc:
            raise ValueError("Invalid EUR-Lex ZIP archive") from exc

        if not metadata.strip():
            raise ValueError("The Formex metadata XML file is empty")

        if not content.strip():
            raise ValueError("The extracted Formex XML file is empty")

        return FormexFiles(
            metadata_xml=metadata,
            content_xml=content,
        )
