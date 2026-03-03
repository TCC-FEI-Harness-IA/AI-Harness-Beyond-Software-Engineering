from collections.abc import AsyncGenerator
import asyncio

class ChainOfThoughtUseCase:
    def __init__(self, ia_adaper: IIaAdapter):
        self.ia_adaper = ia_adaper
    async def execute(self) -> AsyncGenerator[str, None]:

