from abc import ABC, abstractmethod

from src.domain.entities.thinking.ledger_change import LedgerChange
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.enums.result_status_enum import ResultStatusEnum


class IResultsLedger(ABC):
    """Contrato do armazenamento dos resultados de B.3 e do seu estado vigente."""

    @abstractmethod
    def store(self, result: TaskResult) -> LedgerChange:
        """Armazena um resultado aprovado e aplica, de forma atômica, os vereditos aprovados que ele traz.

        Args:
            result: Resultado aprovado em B.2.

        Returns:
            LedgerChange: Resultados substituídos, confirmados, suspensos e restaurados.

        Raises:
            ValueError: Quando o resultado já existe ou alguma referência estruturada é inválida;
                nesse caso nenhum estado muda.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, task_id: str) -> TaskResult:
        """Devolve um resultado armazenado, qualquer que seja o seu estado.

        Raises:
            KeyError: Quando a tarefa não tem resultado armazenado.
        """
        raise NotImplementedError

    @abstractmethod
    def status_of(self, task_id: str) -> ResultStatusEnum:
        """Devolve o estado de um resultado armazenado.

        Raises:
            KeyError: Quando a tarefa não tem resultado armazenado.
        """
        raise NotImplementedError

    @abstractmethod
    def superseded_by(self, task_id: str) -> str | None:
        """Devolve a tarefa revisora que substituiu o resultado, ou `None` quando não foi substituído."""
        raise NotImplementedError

    @abstractmethod
    def current(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados vigentes, na ordem de armazenamento."""
        raise NotImplementedError

    @abstractmethod
    def current_task_ids(self) -> tuple[str, ...]:
        """Devolve os identificadores dos resultados vigentes, na ordem de armazenamento."""
        raise NotImplementedError

    @abstractmethod
    def superseded(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados substituídos, na ordem de armazenamento."""
        raise NotImplementedError

    @abstractmethod
    def awaiting_revalidation(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados que aguardam revalidação, na ordem de armazenamento."""
        raise NotImplementedError

    @abstractmethod
    def reviewable_task_ids(self) -> frozenset[str]:
        """Devolve os resultados que uma tarefa nova pode revisar: vigentes e aguardando revalidação."""
        raise NotImplementedError
