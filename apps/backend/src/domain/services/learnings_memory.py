from typing import Sequence

from src.domain.entities.thinking.learning import Learning
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory

_ITEM_PREFIX = "- "
_ITEM_SEPARATOR = "\n"
_NO_LEARNINGS_CONTENT = "Nenhum aprendizado pontual registrado até o momento."


class LearningsMemory(ILearningsMemory):
    """Armazenamento em memória dos aprendizados pontuais do fluxo (A.3 e B.4)."""

    def __init__(self) -> None:
        """Inicializa o armazenamento vazio."""
        self.__learnings: list[Learning] = []

    def append(self, learnings: Sequence[Learning]) -> tuple[Learning, ...]:
        """Acumula novos aprendizados extraídos por A.3 ou B.4, descartando os já registrados.

        Um aprendizado em branco, ou igual a um já registrado (inclusive no mesmo lote) a menos de
        maiúsculas e espaços, não entra na memória: a área "Aprendizados Pontuais" não repete fatos.
        Reformulações com outras palavras não são detectadas aqui; evitá-las cabe ao template de B.4.

        Args:
            learnings: Aprendizados a acumular.

        Returns:
            tuple[Learning, ...]: Aprendizados efetivamente acumulados, na ordem recebida.
        """
        known = {self.__normalize(content=learning.content) for learning in self.__learnings}
        accepted: list[Learning] = []
        for learning in learnings:
            key = self.__normalize(content=learning.content)
            if not key or key in known:
                continue
            known.add(key)
            accepted.append(learning)

        self.__learnings.extend(accepted)
        return tuple(accepted)

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
        """Renderiza o conteúdo da área "Aprendizados Pontuais" dos templates das fases B e C.

        O título da área pertence a cada template; aqui só se monta o que vai dentro dela.

        Returns:
            str: Lista markdown com um item por aprendizado, na ordem de extração, ou o aviso de
            que ainda não há aprendizados — a área existe em todo prompt, mesmo vazia.
        """
        if self.is_empty():
            return _NO_LEARNINGS_CONTENT

        return _ITEM_SEPARATOR.join(f"{_ITEM_PREFIX}{learning.content}" for learning in self.__learnings)

    def __normalize(self, content: str) -> str:
        """Reduz um aprendizado à forma usada para detectar repetições.

        Args:
            content: Conteúdo do aprendizado.

        Returns:
            str: Conteúdo sem diferenças de maiúsculas e de espaços.
        """
        return " ".join(content.split()).casefold()
