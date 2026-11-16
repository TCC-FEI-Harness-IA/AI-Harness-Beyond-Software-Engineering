from collections import defaultdict, deque
from datetime import datetime, timedelta

from src.domain.errors.execution_limit_exceeded_error import ExecutionLimitExceededError
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.execution_limiter_interface import IExecutionLimiter, IExecutionSlot


class _Slot(IExecutionSlot):
    def __init__(self, limiter: "InMemoryExecutionLimiter", owner_id: str) -> None:
        self.__limiter = limiter
        self.__owner_id = owner_id
        self.__released = False

    def release(self) -> None:
        if not self.__released:
            self.__released = True
            self.__limiter.release(self.__owner_id)


class InMemoryExecutionLimiter(IExecutionLimiter):
    """Limitador em memória do processo.

    O alcance é a instância do backend: com várias réplicas, cada uma aplica os limites às
    execuções que ela atende (documentado no README). Como não há `await` entre a checagem e o
    registro, o limite é consistente no event loop.
    """

    def __init__(self, clock: IClock, max_concurrent: int, max_starts: int, window_seconds: int) -> None:
        """Inicializa o limitador.

        Args:
            clock: Fonte de tempo.
            max_concurrent: Execuções simultâneas por conta.
            max_starts: Inícios por conta dentro da janela.
            window_seconds: Duração da janela deslizante.
        """
        self.clock = clock
        self.max_concurrent = max_concurrent
        self.max_starts = max_starts
        self.window = timedelta(seconds=window_seconds)
        self.__active: dict[str, int] = defaultdict(int)
        self.__starts: dict[str, deque[datetime]] = defaultdict(deque)

    def acquire(self, owner_id: str) -> IExecutionSlot:
        """Ocupa uma vaga, verificando concorrência e inícios recentes."""
        now = self.clock.now()
        starts = self.__starts[owner_id]
        while starts and now - starts[0] >= self.window:
            starts.popleft()
        if self.__active[owner_id] >= self.max_concurrent:
            raise ExecutionLimitExceededError(
                f"Limite de {self.max_concurrent} execuções simultâneas atingido.", retry_after_seconds=30
            )
        if len(starts) >= self.max_starts:
            retry = int((starts[0] + self.window - now).total_seconds())
            raise ExecutionLimitExceededError("Limite de execuções por período atingido.", retry_after_seconds=retry)
        starts.append(now)
        self.__active[owner_id] += 1
        return _Slot(self, owner_id)

    def release(self, owner_id: str) -> None:
        """Libera uma vaga da conta."""
        self.__active[owner_id] = max(0, self.__active[owner_id] - 1)

    def active(self, owner_id: str) -> int:
        """Execuções em andamento da conta."""
        return self.__active[owner_id]
