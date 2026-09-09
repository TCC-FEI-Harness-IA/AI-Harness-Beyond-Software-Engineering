from dataclasses import dataclass


@dataclass(frozen=True)
class Learning:
    """Representa um fato seco e objetivo extraído em B.4.

    Attributes:
        content: Conteúdo sucinto do aprendizado.
        source_task_id: Identificador da tarefa que originou o aprendizado.
    """

    content: str
    source_task_id: str
