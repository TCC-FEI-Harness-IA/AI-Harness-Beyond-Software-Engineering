from abc import ABC, abstractmethod
from typing import Sequence

from src.domain.entities.thinking.learning import Learning


class ILearningsMemory(ABC):
    """Contrato do armazenamento dos aprendizados pontuais do fluxo (A.3 e B.4)."""

    @abstractmethod
    def append(self, learnings: Sequence[Learning]) -> None:
        """Acumula novos aprendizados extraídos por A.3 ou B.4.

        Args:
            learnings: Aprendizados a acumular.
        """
        raise NotImplementedError

    @abstractmethod
    def all(self) -> tuple[Learning, ...]:
        """Devolve todos os aprendizados acumulados até o momento.

        Returns:
            tuple[Learning, ...]: Aprendizados acumulados, em ordem de extração.
        """
        raise NotImplementedError

    @abstractmethod
    def is_empty(self) -> bool:
        """Informa se ainda não há nenhum aprendizado acumulado.

        Returns:
            bool: `True` quando nenhum aprendizado foi acumulado.
        """
        raise NotImplementedError

    @abstractmethod
    def render(self) -> str:
        """Renderiza o conteúdo da área "Aprendizados Pontuais" dos templates das fases B e C.

        Returns:
            str: Lista markdown dos aprendizados acumulados, ou o aviso de que ainda não há nenhum.
        """
        raise NotImplementedError
