from collections.abc import AsyncGenerator
import asyncio

class ChainOfThought:
    async def execute(self) -> AsyncGenerator[str, None]:
        yield "Primeira"
        await asyncio.sleep(0.1)

        yield "Segunda"
        await asyncio.sleep(0.1)

        yield "Terceira"
        await asyncio.sleep(0.1)
