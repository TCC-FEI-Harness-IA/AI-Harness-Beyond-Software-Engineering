from src.domain.entities.thinking.ledger_change import LedgerChange
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.enums.result_status_enum import ResultStatusEnum
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
from src.domain.interfaces.results_ledger_interface import IResultsLedger

_REVIEWABLE = frozenset({ResultStatusEnum.CURRENT, ResultStatusEnum.AWAITING_REVALIDATION})


class ResultsLedger(IResultsLedger):
    """Resultados armazenados em B.3 e o seu estado vigente, mantidos em memória por sessão.

    O estado só muda por referências estruturadas de um resultado aprovado: um veredito
    `superseded` tira o alvo do estado vigente; um veredito `confirmed` mantém o alvo e, se ele
    aguardava revalidação, o restaura. Um resultado que declara depender (`depends_on`) de outro que
    deixou de ser vigente passa a aguardar revalidação, transitivamente. Nada aqui compara textos,
    interpreta palavras ou usa a ordem temporal como evidência; nenhum resultado é apagado.

    A confirmação de um resultado vale como revalidação: as dependências que já não eram vigentes
    nesse momento deixam de suspendê-lo. As confirmações de um mesmo resultado aprovado valem em
    conjunto: todos os confirmados voltam ao estado vigente antes de qualquer base ser filtrada, de
    modo que uma dependência entre dois resultados confirmados juntos é preservada qualquer que seja a
    ordem dos vereditos. Dependentes transitivos de um resultado restaurado não são restaurados
    automaticamente; continuam à espera da própria revisão.
    """

    def __init__(self) -> None:
        """Inicializa o livro vazio."""
        self.__results: dict[str, TaskResult] = {}
        self.__status: dict[str, ResultStatusEnum] = {}
        self.__basis: dict[str, frozenset[str]] = {}
        self.__superseded_by: dict[str, str] = {}

    def store(self, result: TaskResult) -> LedgerChange:
        """Armazena um resultado aprovado e aplica, de forma atômica, os vereditos aprovados que ele traz.

        Toda referência é validada antes de qualquer mudança. As substituições são aplicadas antes das
        confirmações; as confirmações são aplicadas em conjunto, independentemente da ordem dos
        vereditos; e a suspensão por dependência é propagada até estabilizar.

        Args:
            result: Resultado aprovado em B.2.

        Returns:
            LedgerChange: Resultados substituídos, confirmados, suspensos e restaurados.

        Raises:
            ValueError: Quando o resultado já existe ou alguma referência estruturada é inválida;
                nesse caso nenhum estado muda.
        """
        self.__validate(result=result)
        before = dict(self.__status)

        self.__results[result.task_id] = result
        self.__status[result.task_id] = ResultStatusEnum.CURRENT
        self.__basis[result.task_id] = frozenset(result.depends_on)
        superseded = [v.task_id for v in result.revision_verdicts if v.verdict is RevisionVerdictEnum.SUPERSEDED]
        confirmed = [v.task_id for v in result.revision_verdicts if v.verdict is RevisionVerdictEnum.CONFIRMED]
        for task_id in superseded:
            self.__status[task_id] = ResultStatusEnum.SUPERSEDED
            self.__superseded_by[task_id] = result.task_id
        for task_id in confirmed:
            self.__status[task_id] = ResultStatusEnum.CURRENT
        for task_id in confirmed:
            self.__basis[task_id] = frozenset(
                dependency for dependency in self.__basis[task_id] if self.__is_current(task_id=dependency)
            )
        self.__propagate_suspension()

        return LedgerChange(
            superseded_task_ids=tuple(superseded),
            confirmed_task_ids=tuple(confirmed),
            suspended_task_ids=tuple(
                task_id for task_id, status in self.__status.items()
                if status is ResultStatusEnum.AWAITING_REVALIDATION
                and before.get(task_id) is not ResultStatusEnum.AWAITING_REVALIDATION
            ),
            reinstated_task_ids=tuple(
                task_id for task_id in confirmed if before[task_id] is ResultStatusEnum.AWAITING_REVALIDATION
                and self.__is_current(task_id=task_id)
            ),
        )

    def get(self, task_id: str) -> TaskResult:
        """Devolve um resultado armazenado, qualquer que seja o seu estado.

        Args:
            task_id: Tarefa do resultado.

        Returns:
            TaskResult: Resultado armazenado.

        Raises:
            KeyError: Quando a tarefa não tem resultado armazenado.
        """
        return self.__results[task_id]

    def status_of(self, task_id: str) -> ResultStatusEnum:
        """Devolve o estado de um resultado armazenado.

        Args:
            task_id: Tarefa do resultado.

        Returns:
            ResultStatusEnum: Estado atual do resultado.

        Raises:
            KeyError: Quando a tarefa não tem resultado armazenado.
        """
        return self.__status[task_id]

    def superseded_by(self, task_id: str) -> str | None:
        """Devolve a tarefa revisora que substituiu o resultado.

        Args:
            task_id: Tarefa do resultado.

        Returns:
            str | None: Tarefa revisora, ou `None` quando o resultado não foi substituído.
        """
        return self.__superseded_by.get(task_id)

    def current(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados vigentes, na ordem de armazenamento.

        Returns:
            tuple[TaskResult, ...]: Resultados que C.1, C.2 e C.3 recebem como fatos aprovados.
        """
        return self.__with(status=ResultStatusEnum.CURRENT)

    def current_task_ids(self) -> tuple[str, ...]:
        """Devolve os identificadores dos resultados vigentes, na ordem de armazenamento.

        Returns:
            tuple[str, ...]: Identificadores vigentes.
        """
        return tuple(result.task_id for result in self.current())

    def superseded(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados substituídos, na ordem de armazenamento.

        Returns:
            tuple[TaskResult, ...]: Resultados que permanecem só na auditoria.
        """
        return self.__with(status=ResultStatusEnum.SUPERSEDED)

    def awaiting_revalidation(self) -> tuple[TaskResult, ...]:
        """Devolve os resultados que aguardam revalidação, na ordem de armazenamento.

        Returns:
            tuple[TaskResult, ...]: Resultados suspensos por dependência explícita.
        """
        return self.__with(status=ResultStatusEnum.AWAITING_REVALIDATION)

    def reviewable_task_ids(self) -> frozenset[str]:
        """Devolve os resultados que uma tarefa nova pode revisar.

        Returns:
            frozenset[str]: Resultados vigentes e aguardando revalidação; substituídos ficam de fora.
        """
        return frozenset(task_id for task_id, status in self.__status.items() if status in _REVIEWABLE)

    def __validate(self, result: TaskResult) -> None:
        """Valida as referências do resultado sem alterar nada.

        Raises:
            ValueError: Quando o resultado já foi armazenado; quando um veredito aponta o próprio
                resultado, um resultado inexistente ou substituído, ou repete um alvo; ou quando uma
                dependência aponta o próprio resultado, um inexistente ou um alvo da revisão.
        """
        task_id = result.task_id
        if task_id in self.__results:
            raise ValueError(f"O resultado da tarefa '{task_id}' já foi armazenado.")

        targets = [verdict.task_id for verdict in result.revision_verdicts]
        for target in targets:
            if target == task_id:
                raise ValueError(f"A tarefa '{task_id}' não pode revisar a si mesma.")
            if target not in self.__results:
                raise ValueError(f"'{target}' não é um resultado armazenado e não pode ser revisado por '{task_id}'.")
            if self.__status[target] not in _REVIEWABLE:
                raise ValueError(f"O resultado '{target}' já foi substituído e não pode ser revisado.")
        if len(set(targets)) != len(targets):
            raise ValueError(f"A tarefa '{task_id}' traz mais de um veredito para o mesmo resultado.")

        for dependency in result.depends_on:
            if dependency == task_id:
                raise ValueError(f"A tarefa '{task_id}' não pode depender de si mesma.")
            if dependency not in self.__results:
                raise ValueError(f"'{dependency}' não é um resultado armazenado e não pode ser dependência.")
            if dependency in targets:
                raise ValueError(f"A tarefa '{task_id}' não pode depender de um resultado que revisa.")

    def __propagate_suspension(self) -> None:
        """Suspende, até estabilizar, todo resultado vigente cuja base declarada deixou de ser vigente."""
        changed = True
        while changed:
            changed = False
            for task_id, basis in self.__basis.items():
                if self.__is_current(task_id=task_id) and not all(self.__is_current(task_id=d) for d in basis):
                    self.__status[task_id] = ResultStatusEnum.AWAITING_REVALIDATION
                    changed = True

    def __is_current(self, task_id: str) -> bool:
        """Informa se o resultado está vigente.

        Returns:
            bool: `True` quando o estado é `current`.
        """
        return self.__status[task_id] is ResultStatusEnum.CURRENT

    def __with(self, status: ResultStatusEnum) -> tuple[TaskResult, ...]:
        """Filtra os resultados pelo estado, na ordem de armazenamento.

        Returns:
            tuple[TaskResult, ...]: Resultados no estado informado.
        """
        return tuple(self.__results[task_id] for task_id, current in self.__status.items() if current is status)
