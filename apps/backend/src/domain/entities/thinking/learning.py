from dataclasses import dataclass


@dataclass(frozen=True)
class Learning:
    """Representa um fato seco e objetivo extraído em A.3 (do enunciado) ou em B.4 (de uma tarefa).

    Attributes:
        content: Conteúdo sucinto do aprendizado.
        source_task_id: Identificador da tarefa que originou o aprendizado, ou `None` quando ele
            vem do enunciado (A.3) e portanto não pertence a nenhuma tarefa.
    """

    content: str
    source_task_id: str | None = None
