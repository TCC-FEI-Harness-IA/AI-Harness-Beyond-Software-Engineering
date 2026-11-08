from dataclasses import dataclass


@dataclass(frozen=True)
class LedgerChange:
    """Mudança de estado provocada pelo armazenamento de um resultado em B.3.

    Attributes:
        superseded_task_ids: Resultados que um veredito aprovado substituiu.
        confirmed_task_ids: Resultados que um veredito aprovado confirmou.
        suspended_task_ids: Resultados que passaram a aguardar revalidação, inclusive o recém-armazenado.
        reinstated_task_ids: Resultados em revalidação que voltaram a ser vigentes por confirmação.
    """

    superseded_task_ids: tuple[str, ...] = ()
    confirmed_task_ids: tuple[str, ...] = ()
    suspended_task_ids: tuple[str, ...] = ()
    reinstated_task_ids: tuple[str, ...] = ()

    @property
    def withdrawn_task_ids(self) -> tuple[str, ...]:
        """Resultados que deixaram de ser vigentes: substituídos e suspensos.

        Returns:
            tuple[str, ...]: Identificadores cujos aprendizados saem da visão vigente.
        """
        return (*self.superseded_task_ids, *self.suspended_task_ids)

    def is_empty(self) -> bool:
        """Informa se o armazenamento não mudou o estado de nenhum resultado anterior.

        Returns:
            bool: `True` quando não há substituição, confirmação, suspensão nem restauração.
        """
        return not (
            self.superseded_task_ids or self.confirmed_task_ids or self.suspended_task_ids or self.reinstated_task_ids
        )
