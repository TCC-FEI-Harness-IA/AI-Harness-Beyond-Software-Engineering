from abc import ABC, abstractmethod
from collections.abc import Callable

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest


class IBenchmarkFlowRunner(ABC):
    """Contrato de execução de um fluxo de inferência para uma questão do benchmark."""

    @abstractmethod
    async def run(
        self,
        request: BenchmarkFlowRequest,
        on_tokens: Callable[[int], None],
    ) -> BenchmarkFlowOutcome:
        """Executa o fluxo pedido, persiste a sessão e a avaliação, e devolve o desfecho.

        Falhas do fluxo nunca são levantadas: viram um desfecho com `error`, para que não
        impeçam o outro fluxo nem as próximas questões. Só o cancelamento é propagado.

        Args:
            request: Questão, fluxo, prompt e configuração do modelo.
            on_tokens: Chamado com o consumo acumulado sempre que o fluxo o informa.

        Returns:
            BenchmarkFlowOutcome: Desfecho avaliado do fluxo.
        """
        raise NotImplementedError
