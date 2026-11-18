from datetime import date
from uuid import uuid4

from ingestion_worker.domain.documents import DocumentLanguage


def create_collection_name(celex: str, consolidation_date: date, language: DocumentLanguage) -> str:
    normalized_celex = celex.lower().replace("-", "").replace("/", "_")
    build_id = uuid4().hex[:12]

    return f"eu_ai_act_{normalized_celex}_{consolidation_date:%Y%m%d}_{language.lower()}_{build_id}"
