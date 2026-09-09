from abc import ABC, abstractmethod
from typing import Sequence

from src.domain.entities.thinking.task import Task


class ITaskQueue(ABC):
    """Contrato da fila de tarefas do loop de execução."""

    @abstractmethod
    def push_back(self, tasks: Sequence[Task]) -> None:
        """Enfileira tarefas no fim da fila.

        Args:
            tasks: Tarefas a enfileirar, produzidas por A.2.
        """
        raise NotImplementedError

    @abstractmethod
    def push_front(self, tasks: Sequence[Task]) -> None:
        """Insere tarefas no topo da fila.

        Args:
            tasks: Tarefas a inserir, produzidas por C.2.
        """
        raise NotImplementedError

    @abstractmethod
    def pop_next(self) -> Task | None:
        """Retira a próxima tarefa da fila, de forma puramente programática.

        Returns:
            Task | None: Próxima tarefa, ou `None` quando a fila está vazia.
        """
        raise NotImplementedError

    @abstractmethod
    def is_empty(self) -> bool:
        """Informa se a fila está vazia.

        Returns:
            bool: `True` quando não há tarefas pendentes.
        """
        raise NotImplementedError

    @abstractmethod
    def discard_all(self) -> list[Task]:
        """Descarta todas as tarefas restantes na fila.

        Returns:
            list[Task]: Tarefas descartadas.
        """
        raise NotImplementedError

    @abstractmethod
    def total_created(self) -> int:
        """Total de tarefas já enfileiradas na sessão, incluindo as consumidas.

        Returns:
            int: Total de tarefas criadas na sessão.
        """
        raise NotImplementedError
