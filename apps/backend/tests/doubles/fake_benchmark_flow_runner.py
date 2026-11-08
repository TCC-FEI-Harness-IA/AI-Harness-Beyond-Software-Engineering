import asyncio
from collections.abc import Awaitable, Callable

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.interfaces.benchmark_flow_runner_interface import IBenchmarkFlowRunner

Behavior = Callable[[BenchmarkFlowRequest, Callable[[int], None]], Awaitable[BenchmarkFlowOutcome]]


class FakeBenchmarkFlowRunner(IBenchmarkFlowRunner):
    """Dublê de `IBenchmarkFlowRunner` que registra os pedidos e delega a um comportamento programado.

    Mede quantas questões ficam ativas ao mesmo tempo, para verificar o limite de paralelismo.
    """

    def __init__(self, behavior: Behavior) -> None:
        """Configura o dublê.

        Args:
            behavior: Corrotina que produz o desfecho de cada pedido.
        """
        self.behavior = behavior
        self.requests: list[BenchmarkFlowRequest] = []
        self.active: set[str] = set()
        self.max_active = 0
        self.cancelled: list[BenchmarkFlowRequest] = []

    async def run(self, request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        """Registra o pedido e executa o comportamento programado."""
        self.requests.append(request)
        self.active.add(request.question.id)
        self.max_active = max(self.max_active, len(self.active))
        try:
            return await self.behavior(request, on_tokens)
        except asyncio.CancelledError:
            self.cancelled.append(request)
            raise
        finally:
            self.active.discard(request.question.id)
