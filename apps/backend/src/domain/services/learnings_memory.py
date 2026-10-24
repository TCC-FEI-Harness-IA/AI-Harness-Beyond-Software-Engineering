from typing import Sequence

from src.domain.entities.thinking.learning import Learning
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory

_BLOCK_HEADING = "## Aprendizados acumulados"
_BLOCK_SEPARATOR = "\n\n"
_ITEM_PREFIX = "- "
_ITEM_SEPARATOR = "\n"
_EMPTY_BLOCK = ""


class LearningsMemory(ILearningsMemory):
    """Armazenamento em memória dos aprendizados pontuais do loop de execução."""

    def __init__(self) -> None:
        """Inicializa o armazenamento vazio."""
        self.__learnings: list[Learning] = []

    def append(self, learnings: Sequence[Learning]) -> None:
        """Acumula novos aprendizados extraídos por A.3 ou B.4.

        Args:
            learnings: Aprendizados a acumular.
        """
        self.__learnings.extend(learnings)

    def all(self) -> tuple[Learning, ...]:
        """Devolve todos os aprendizados acumulados até o momento.

        Returns:
            tuple[Learning, ...]: Aprendizados acumulados, em ordem de extração.
        """
        return tuple(self.__learnings)

    def is_empty(self) -> bool:
        """Informa se ainda não há nenhum aprendizado acumulado.

        Returns:
            bool: `True` quando nenhum aprendizado foi acumulado.
        """
        return not self.__learnings

    def render(self) -> str:
        """Renderiza os aprendizados acumulados como bloco markdown.

        Returns:
            str: Bloco markdown pronto para injeção no início de um novo contexto,
            ou string vazia quando ainda não há aprendizados.
        """
        if self.is_empty():
            return _EMPTY_BLOCK

        items = _ITEM_SEPARATOR.join(f"{_ITEM_PREFIX}{learning.content}" for learning in self.__learnings)
        return f"{_BLOCK_HEADING}{_BLOCK_SEPARATOR}{items}"
