from dataclasses import dataclass, field
from typing import Iterable, Sequence

from src.domain.entities.thinking.learning import Learning
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory

_ITEM_TEMPLATE = "- [{origin}] {content}"
_ITEM_SEPARATOR = "\n"
_NO_LEARNINGS_CONTENT = "No key learnings recorded so far."
# Rótulos de procedência (refinamentos 03). Indicam só a origem da nota — o enunciado ou as tarefas vigentes
# que a registraram —, nunca a sua veracidade. "Question" evita depender do número da fase de extração,
# que é A.3 no fluxo versão 1 e A.4 no fluxo versão 2.
_QUESTION_ORIGIN = "Question"
_TASK_ORIGIN = "Task {ids}"
_TASKS_ORIGIN = "Tasks {ids}"
_ORIGIN_SEPARATOR = "; "
_TASK_IDS_SEPARATOR = ", "


@dataclass
class _Entry:
    """Um fato registrado, com o primeiro texto recebido e todas as fontes que o registraram."""

    learning: Learning
    sources: list[str | None] = field(default_factory=list)


class LearningsMemory(ILearningsMemory):
    """Armazenamento em memória dos aprendizados pontuais do fluxo (A.3 e B.4), com proveniência.

    Cada fato guarda todas as fontes que o registraram: o enunciado (A.3, fonte `None`) e as
    tarefas (B.4). A visão vigente — a área "Aprendizados Pontuais" — contém os fatos com ao menos
    uma fonte vigente. Retirar uma tarefa (porque o seu resultado foi substituído ou aguarda
    revalidação) só tira da visão os fatos que não têm outra fonte vigente; o enunciado é sempre
    fonte vigente. Nada é apagado: restaurar a fonte devolve os fatos à visão.
    """

    def __init__(self) -> None:
        """Inicializa o armazenamento vazio."""
        self.__entries: list[_Entry] = []
        self.__withdrawn_sources: set[str] = set()

    def append(self, learnings: Sequence[Learning]) -> tuple[Learning, ...]:
        """Acumula novos aprendizados extraídos por A.3 ou B.4, descartando os já registrados.

        Um aprendizado em branco, ou igual a um já registrado (inclusive no mesmo lote) a menos de
        espaços, não entra de novo na área "Aprendizados Pontuais": a repetição só acrescenta a sua
        fonte ao fato já registrado, para que ele continue sustentado se a primeira fonte for retirada.
        Reformulações com outras palavras não são detectadas aqui; evitá-las cabe ao template de B.4.
        A normalização serve só à comparação: o primeiro conteúdo permanece intacto.
        Referentes, unidades, caixa, condições e aproximações diferentes não são equivalentes.
        Um aprendizado de fonte retirada é registrado, mas não entra na visão vigente.

        Args:
            learnings: Aprendizados a acumular.

        Returns:
            tuple[Learning, ...]: Aprendizados que passaram a fazer parte da visão vigente, na ordem
            recebida: os novos de fonte vigente e os já registrados que uma fonte vigente reativou.
        """
        accepted: list[Learning] = []
        for learning in learnings:
            key = self.__normalize(content=learning.content)
            if not key:
                continue
            entry = next((item for item in self.__entries if self.__normalize(item.learning.content) == key), None)
            if entry is None:
                entry = _Entry(learning=learning)
                self.__entries.append(entry)
            was_visible = self.__is_visible(entry=entry)
            if learning.source_task_id not in entry.sources:
                entry.sources.append(learning.source_task_id)
            if not was_visible and self.__is_visible(entry=entry):
                accepted.append(learning)
        return tuple(accepted)

    def withdraw(self, task_ids: Iterable[str]) -> tuple[Learning, ...]:
        """Retira as tarefas informadas das fontes vigentes.

        Args:
            task_ids: Tarefas cujos resultados deixaram de ser vigentes.

        Returns:
            tuple[Learning, ...]: Aprendizados que saíram da visão vigente, por não terem outra fonte.
        """
        before = self.all()
        self.__withdrawn_sources.update(task_ids)
        current = self.all()
        return tuple(learning for learning in before if learning not in current)

    def restore(self, task_ids: Iterable[str]) -> tuple[Learning, ...]:
        """Devolve as tarefas informadas às fontes vigentes.

        Args:
            task_ids: Tarefas cujos resultados voltaram a ser vigentes.

        Returns:
            tuple[Learning, ...]: Aprendizados que voltaram à visão vigente, na ordem de registro.
        """
        before = self.all()
        self.__withdrawn_sources.difference_update(task_ids)
        return tuple(learning for learning in self.all() if learning not in before)

    def all(self) -> tuple[Learning, ...]:
        """Devolve a visão vigente: os aprendizados com ao menos uma fonte vigente.

        Returns:
            tuple[Learning, ...]: Aprendizados vigentes, em ordem de primeiro registro.
        """
        return tuple(entry.learning for entry in self.__entries if self.__is_visible(entry=entry))

    def is_empty(self) -> bool:
        """Informa se a visão vigente não tem nenhum aprendizado.

        Returns:
            bool: `True` quando nenhum aprendizado está vigente.
        """
        return not self.all()

    def render(self) -> str:
        """Renderiza o conteúdo da área "Aprendizados Pontuais" dos templates das fases B e C.

        O título da área pertence a cada template; aqui só se monta o que vai dentro dela. Cada item
        começa pelo rótulo de procedência, montado a partir das fontes vigentes do fato: `[Question]`
        para o enunciado, `[Task T1]` ou `[Tasks T1, T3]` para as tarefas, e `[Question; Task T2]` quando
        há as duas origens. Uma fonte retirada não aparece, mesmo que seja a do primeiro registro. O
        rótulo é só apresentação: não entra no conteúdo armazenado nem na chave de deduplicação.

        Returns:
            str: Lista markdown com um item rotulado por aprendizado vigente, na ordem de extração, ou o
            aviso de que ainda não há aprendizados — a área existe em todo prompt, mesmo vazia.
        """
        visible = [entry for entry in self.__entries if self.__is_visible(entry=entry)]
        if not visible:
            return _NO_LEARNINGS_CONTENT

        return _ITEM_SEPARATOR.join(
            _ITEM_TEMPLATE.format(origin=self.__render_origin(entry=entry), content=entry.learning.content)
            for entry in visible
        )

    def __render_origin(self, entry: _Entry) -> str:
        """Monta o rótulo de procedência de um fato com as suas fontes vigentes.

        Args:
            entry: Fato registrado, com todas as fontes que o registraram.

        Returns:
            str: O enunciado primeiro, quando é fonte, seguido das tarefas vigentes na ordem de registro.
        """
        origins: list[str] = []
        if None in entry.sources:
            origins.append(_QUESTION_ORIGIN)
        task_ids = [
            source for source in entry.sources if source is not None and source not in self.__withdrawn_sources
        ]
        if task_ids:
            template = _TASK_ORIGIN if len(task_ids) == 1 else _TASKS_ORIGIN
            origins.append(template.format(ids=_TASK_IDS_SEPARATOR.join(task_ids)))
        return _ORIGIN_SEPARATOR.join(origins)

    def __is_visible(self, entry: _Entry) -> bool:
        """Informa se o fato tem ao menos uma fonte vigente.

        Returns:
            bool: `True` quando alguma fonte é o enunciado ou uma tarefa não retirada.
        """
        return any(source is None or source not in self.__withdrawn_sources for source in entry.sources)

    def __normalize(self, content: str) -> str:
        """Reduz um aprendizado à forma usada para detectar repetições.

        Args:
            content: Conteúdo do aprendizado.

        Returns:
            str: Conteúdo com espaços normalizados, preservando maiúsculas e símbolos.
        """
        return " ".join(content.split())
