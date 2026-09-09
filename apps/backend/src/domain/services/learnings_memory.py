from typing import Sequence

from src.domain.entities.thinking.learning import Learning
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory


class LearningsMemory(ILearningsMemory):
    """Armazenamento em memória dos aprendizados pontuais do loop de execução."""

    def __init__(self) -> None:
        """Inicializa o armazenamento vazio."""
        self.__learnings: list[Learning] = []

    def append(self, learnings: Sequence[Learning]) -> None:
        """Acumula novos aprendizados extraídos por B.4.

        Args:
            learnings: Aprendizados a acumular.
        """
        raise NotImplementedError

    def all(self) -> tuple[Learning, ...]:
        """Devolve todos os aprendizados acumulados até o momento.

        Returns:
            tuple[Learning, ...]: Aprendizados acumulados, em ordem de extração.
        """
        raise NotImplementedError

    def is_empty(self) -> bool:
        """Informa se ainda não há nenhum aprendizado acumulado.

        Returns:
            bool: `True` quando nenhum aprendizado foi acumulado.
        """
        raise NotImplementedError

    def render(self) -> str:
        """Renderiza os aprendizados acumulados como bloco markdown.

        Returns:
            str: Bloco markdown pronto para injeção no início de um novo contexto.
        """
        raise NotImplementedError
