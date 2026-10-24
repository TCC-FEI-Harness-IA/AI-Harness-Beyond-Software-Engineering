from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationContext:
    """Dados esperados pela chamada, usados para validar a saída estruturada de uma fase.

    Cada fase preenche apenas o que lhe diz respeito: as verificações (B.2 e C.1) informam
    os critérios que precisam ser avaliados; o planejamento (A.2 e C.2) informa o teto de
    tarefas aceito e os identificadores de tarefa que já existem na sessão.

    Attributes:
        expected_criteria_ids: Identificadores dos critérios que a verificação deve avaliar,
            um a um. `None` fora das fases de verificação.
        max_tasks: Quantidade máxima de tarefas que o lote planejado pode ter. `None` quando
            a fase não planeja tarefas ou não há teto.
        known_task_ids: Identificadores de tarefa já usados na sessão, que o lote não pode repetir.
    """

    expected_criteria_ids: tuple[str, ...] | None = None
    max_tasks: int | None = None
    known_task_ids: frozenset[str] = frozenset()
