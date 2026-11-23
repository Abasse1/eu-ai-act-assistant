
from typing import Protocol


class EmbeddingGenerator(Protocol):
    async def generate(self,text: str) -> list[float]: ...