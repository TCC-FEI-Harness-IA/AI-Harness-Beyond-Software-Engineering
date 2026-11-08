from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewRequest:
    """Pedido de revisão planejado por C.2: quais resultados armazenados a tarefa investiga e por quê.

    O pedido aponta candidatos sob investigação; não decide o desfecho. Só a execução da tarefa,
    aprovada em B.2, pode confirmar ou substituir os resultados apontados.

    Attributes:
        task_ids: Tarefas cujos resultados armazenados serão investigados, sem repetição.
        reason: Motivo concreto da investigação, vindo do relatório de C.1.
    """

    task_ids: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        """Recusa um pedido sem alvo, com alvo repetido ou em branco, ou sem motivo.

        Raises:
            ValueError: Quando o pedido não identifica de forma inequívoca o que investigar.
        """
        if not self.task_ids:
            raise ValueError("Um pedido de revisão precisa apontar ao menos um resultado.")
        if len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("Um pedido de revisão não pode repetir um resultado.")
        if any(not task_id.strip() for task_id in self.task_ids):
            raise ValueError("Um pedido de revisão não pode apontar um identificador em branco.")
        if not self.reason.strip():
            raise ValueError("Um pedido de revisão precisa declarar o motivo da investigação.")
