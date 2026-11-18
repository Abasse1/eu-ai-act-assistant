from ingestion_worker.application.indexing.vector_indexer import VectorIndexer


async def validate_collection(
    indexer: VectorIndexer,
    collection_name: str,
    expected_count: int,
) -> None:
    if expected_count <= 0:
        raise ValueError("Expected point count must be greater than zero")

    actual_count = await indexer.count(collection_name)

    if actual_count != expected_count:
        raise RuntimeError(
            f"Incomplete collection '{collection_name}': "
            f"expected {expected_count} points, found {actual_count}"
        )
