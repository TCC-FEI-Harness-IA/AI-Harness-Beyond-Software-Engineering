from typing import Sequence

from src.domain.entities.thinking.task import Task
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.interfaces.task_queue_interface import ITaskQueue

_FIRST_POSITION = 0


class TaskQueue(ITaskQueue):
    """Fila de tarefas do loop de execução, mantida em memória por sessão."""

    def __init__(self) -> None:
        """Inicializa a fila vazia."""
        self.__tasks: list[Task] = []
        self.__total_created = 0
        self.__known_ids: set[str] = set()

    def push_back(self, tasks: Sequence[Task]) -> None:
        """Enfileira tarefas no fim da fila.

        Args:
            tasks: Tarefas a enfileirar, produzidas por A.2.

        Raises:
            ValueError: Quando alguma tarefa repete um identificador já enfileirado.
        """
        self.__register(tasks=tasks)
        self.__tasks.extend(tasks)

    def push_front(self, tasks: Sequence[Task]) -> None:
        """Insere tarefas no topo da fila, preservando a ordem relativa entre elas.

        Args:
            tasks: Tarefas a inserir, produzidas por C.2.

        Raises:
            ValueError: Quando alguma tarefa repete um identificador já enfileirado.
        """
        self.__register(tasks=tasks)
        self.__tasks[_FIRST_POSITION:_FIRST_POSITION] = tasks

    def pop_next(self) -> Task | None:
        """Retira a próxima tarefa da fila, de forma puramente programática.

        Returns:
            Task | None: Próxima tarefa, já marcada como em andamento, ou `None`
            quando a fila está vazia.
        """
        if not self.__tasks:
            return None

        task = self.__tasks.pop(_FIRST_POSITION)
        task.status = TaskStatusEnum.IN_PROGRESS
        return task

    def is_empty(self) -> bool:
        """Informa se a fila está vazia.

        Returns:
            bool: `True` quando não há tarefas pendentes.
        """
        return not self.__tasks

    def discard_all(self) -> list[Task]:
        """Descarta todas as tarefas restantes na fila.

        Returns:
            list[Task]: Tarefas descartadas, já marcadas como descartadas.
        """
        discarded = self.__tasks
        self.__tasks = []

        for task in discarded:
            task.status = TaskStatusEnum.DISCARDED

        return discarded

    def total_created(self) -> int:
        """Total de tarefas já enfileiradas na sessão, incluindo as consumidas.

        Returns:
            int: Total de tarefas criadas na sessão.
        """
        return self.__total_created

    def known_task_ids(self) -> frozenset[str]:
        """Identificadores de todas as tarefas já enfileiradas na sessão, inclusive as consumidas.

        Returns:
            frozenset[str]: Identificadores que um novo lote de tarefas não pode repetir.
        """
        return frozenset(self.__known_ids)

    def __register(self, tasks: Sequence[Task]) -> None:
        """Registra os identificadores do lote de forma atômica, recusando colisões.

        O lote inteiro é validado antes de qualquer alteração: se ele for recusado, nenhum
        identificador nem contador muda.

        Args:
            tasks: Tarefas prestes a entrar na fila.

        Raises:
            ValueError: Quando alguma tarefa repete um identificador já enfileirado ou
                repetido dentro do próprio lote.
        """
        batch_ids: set[str] = set()
        for task in tasks:
            if task.id in self.__known_ids or task.id in batch_ids:
                raise ValueError(f"A tarefa '{task.id}' já foi enfileirada nesta sessão.")
            batch_ids.add(task.id)

        self.__known_ids.update(batch_ids)
        self.__total_created += len(tasks)
