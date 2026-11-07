from dataclasses import dataclass


@dataclass(frozen=True)
class TaskResult:
    """Representa o resultado aprovado de uma tarefa, armazenado em B.3.

    Só existe resultado para uma tarefa aprovada; ver `Task.approved_result`.

    Attributes:
        task_id: Identificador da tarefa que originou o resultado.
        task_title: Título da tarefa que originou o resultado.
        task_description: Enunciado da tarefa que originou o resultado.
        content: Conteúdo aprovado da resolução da tarefa.
        conclusion: Conclusão final do conteúdo aprovado, sem o raciocínio que levou a ela.
    """

    task_id: str
    task_title: str
    task_description: str
    content: str
    conclusion: str
