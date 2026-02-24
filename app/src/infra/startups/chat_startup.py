from collections.abc import AsyncGenerator

from src.usecases.chain_of_thought import ChainOfThought


class ChatStartup:
    def __init__(self) -> None:
        self.chain_of_thought = ChainOfThought()

    async def run(self) -> AsyncGenerator[str, None]:
        async for thought in self.chain_of_thought.execute():
            yield f"data: {thought}\n\n"
