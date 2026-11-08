from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from src.domain.entities.thinking.learning import Learning


class ILearningsMemory(ABC):
    """Contrato do armazenamento dos aprendizados pontuais do fluxo (A.3 e B.4).

    A memória guarda a proveniência de cada fato. A visão vigente — o que `all` e `render`
    devolvem — contém só os fatos com ao menos uma fonte vigente; o enunciado (A.3) é sempre vigente.
    """

    @abstractmethod
    def append(self, learnings: Sequence[Learning]) -> tuple[Learning, ...]:
        """Acumula novos aprendizados extraídos por A.3 ou B.4, descartando os já registrados.

        Compara apenas normalizando espaços. Preserva o primeiro texto e a ordem; uma repetição
        acrescenta a sua fonte ao fato já registrado. Não interpreta equivalências de símbolos,
        valores, unidades, referentes ou condições.

        Args:
            learnings: Aprendizados a acumular.

        Returns:
            tuple[Learning, ...]: Aprendizados que passaram a fazer parte da visão vigente, na ordem recebida.
        """
        raise NotImplementedError

    @abstractmethod
    def withdraw(self, task_ids: Iterable[str]) -> tuple[Learning, ...]:
        """Retira tarefas das fontes vigentes, sem apagar o que elas registraram.

        Args:
            task_ids: Tarefas cujos resultados deixaram de ser vigentes.

        Returns:
            tuple[Learning, ...]: Aprendizados que saíram da visão vigente por não terem outra fonte.
        """
        raise NotImplementedError

    @abstractmethod
    def restore(self, task_ids: Iterable[str]) -> tuple[Learning, ...]:
        """Devolve tarefas às fontes vigentes.

        Args:
            task_ids: Tarefas cujos resultados voltaram a ser vigentes.

        Returns:
            tuple[Learning, ...]: Aprendizados que voltaram à visão vigente.
        """
        raise NotImplementedError

    @abstractmethod
    def all(self) -> tuple[Learning, ...]:
        """Devolve a visão vigente dos aprendizados acumulados.

        Returns:
            tuple[Learning, ...]: Aprendizados com fonte vigente, em ordem de extração.
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
