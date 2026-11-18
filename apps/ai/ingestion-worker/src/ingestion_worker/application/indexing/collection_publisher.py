from typing import Protocol


class CollectionPublisher(Protocol):
    async def publish(self, collection_name: str) -> None: ...
