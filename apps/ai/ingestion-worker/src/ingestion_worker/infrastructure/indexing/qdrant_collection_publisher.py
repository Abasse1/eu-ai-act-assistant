from qdrant_client import AsyncQdrantClient, models

from ingestion_worker.application.indexing.collection_publisher import CollectionPublisher


class QdrantCollectionPublisher(CollectionPublisher):
    def __init__(self, client: AsyncQdrantClient, active_alias: str) -> None:
        self._client = client
        self._active_alias = active_alias

    async def publish(self, collection_name: str) -> None:
        if not await self._client.collection_exists(collection_name):
            raise ValueError(f"Collection does not exist: {collection_name}")

        aliases = await self._client.get_aliases()

        current_alias = next(
            (alias for alias in aliases.aliases if alias.alias_name == self._active_alias),
            None,
        )

        if current_alias and current_alias.collection_name == collection_name:
            return

        operations: list[models.AliasOperations] = []

        if current_alias:
            operations.append(
                models.DeleteAliasOperation(
                    delete_alias=models.DeleteAlias(alias_name=self._active_alias)
                )
            )

        operations.append(
            models.CreateAliasOperation(
                create_alias=models.CreateAlias(
                    collection_name=collection_name,
                    alias_name=self._active_alias,
                )
            )
        )

        await self._client.update_collection_aliases(change_aliases_operations=operations)
