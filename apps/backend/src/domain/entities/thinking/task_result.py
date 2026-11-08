from dataclasses import dataclass

from src.domain.entities.thinking.revision_verdict import RevisionVerdict


@dataclass(frozen=True)
class TaskResult:
    """Representa o resultado aprovado de uma tarefa, armazenado em B.3.

    Só existe resultado para uma tarefa aprovada; ver `Task.approved_result`. O estado vigente do
    resultado (vigente, substituído ou aguardando revalidação) é mantido pelo livro de resultados.

    Attributes:
        task_id: Identificador da tarefa que originou o resultado.
        task_title: Título da tarefa que originou o resultado.
        task_description: Enunciado da tarefa que originou o resultado.
        content: Conteúdo aprovado da resolução da tarefa.
        conclusion: Conclusão final do conteúdo aprovado, sem o raciocínio que levou a ela.
        depends_on: Tarefas cujos resultados o planejamento declarou como base desta conclusão.
        revision_verdicts: Vereditos aprovados sobre resultados investigados; vazio numa tarefa normal.
    """

    task_id: str
    task_title: str
    task_description: str
    content: str
    conclusion: str
    depends_on: tuple[str, ...] = ()
    revision_verdicts: tuple[RevisionVerdict, ...] = ()
