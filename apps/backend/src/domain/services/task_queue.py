from typing import Sequence

from src.domain.entities.thinking.task import Task
from src.domain.interfaces.task_queue_interface import ITaskQueue


class TaskQueue(ITaskQueue):
    """Fila de tarefas do loop de execução, mantida em memória por sessão."""

    def __init__(self) -> None:
        """Inicializa a fila vazia."""
        self.__tasks: list[Task] = []
        self.__total_created = 0

    def push_back(self, tasks: Sequence[Task]) -> None:
        """Enfileira tarefas no fim da fila.

        Args:
            tasks: Tarefas a enfileirar, produzidas por A.2.
        """
        raise NotImplementedError

    def push_front(self, tasks: Sequence[Task]) -> None:
        """Insere tarefas no topo da fila.

        Args:
            tasks: Tarefas a inserir, produzidas por C.2.
        """
        raise NotImplementedError

    def pop_next(self) -> Task | None:
        """Retira a próxima tarefa da fila, de forma puramente programática.

        Returns:
            Task | None: Próxima tarefa, ou `None` quando a fila está vazia.
        """
        raise NotImplementedError

    def is_empty(self) -> bool:
        """Informa se a fila está vazia.

        Returns:
            bool: `True` quando não há tarefas pendentes.
        """
        raise NotImplementedError

    def discard_all(self) -> list[Task]:
        """Descarta todas as tarefas restantes na fila.

        Returns:
            list[Task]: Tarefas descartadas.
        """
        raise NotImplementedError

    def total_created(self) -> int:
        """Total de tarefas já enfileiradas na sessão, incluindo as consumidas.

        Returns:
            int: Total de tarefas criadas na sessão.
        """
        raise NotImplementedError
