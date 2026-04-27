from collections.abc import AsyncGenerator
import asyncio


class SendReasoningMessageUsecase:
    def __init__(self):
        ...

    async def execute(self, user_input: str) -> AsyncGenerator[str, None]:
        chunks = [
            f"Entrada recebida: {user_input}",
            "Fase 1: analisando contexto...",
            "Fase 2: estruturando raciocínio...",
            "Fase 3: consolidando resposta...",
        ]

        for chunk in chunks:
            yield chunk
            await asyncio.sleep(1)

