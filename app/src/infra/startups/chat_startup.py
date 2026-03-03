from collections.abc import AsyncGenerator

from src.usecases.chain_of_thought_usecase import ChainOfThoughtUseCase


class ChatStartup:
    def __init__(self) -> None:
        self.chain_of_thought_use_case = ChainOfThoughtUseCase()

    async def run(self) -> AsyncGenerator[str, None]:
        async for thought in self.chain_of_thought_use_case.execute():
            yield f"data: {thought}\n\n"
