from abc import ABC, abstractmethod
from types import TracebackType


class IExecutionSlot(ABC):
    """Vaga ocupada por uma execução; liberá-la mais de uma vez não tem efeito."""

    @abstractmethod
    def release(self) -> None:
        """Libera a vaga."""
        raise NotImplementedError

    def __enter__(self) -> "IExecutionSlot":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self.release()


class IExecutionLimiter(ABC):
    """Limita, por conta, execuções LLM simultâneas e inícios numa janela de tempo."""

    @abstractmethod
    def acquire(self, owner_id: str) -> IExecutionSlot:
        """Ocupa uma vaga para a conta.

        Raises:
            ExecutionLimitExceededError: Quando algum limite foi atingido.
        """
        raise NotImplementedError

    @abstractmethod
    def active(self, owner_id: str) -> int:
        """Execuções em andamento da conta."""
        raise NotImplementedError
