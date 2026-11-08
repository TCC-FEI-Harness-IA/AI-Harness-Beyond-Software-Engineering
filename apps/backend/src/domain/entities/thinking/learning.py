from dataclasses import dataclass


@dataclass(frozen=True)
class Learning:
    """Representa uma nota autossuficiente de A.3 (dado literal) ou B.4 (conclusão derivada).

    O texto conserva associações, referentes, unidades, condições e qualificações. Números e
    símbolos permanecem no texto: o harness aceita pedidos genéricos, sem interpretar o domínio.
    A completude semântica é uma obrigação dos templates, não uma validação desta entidade.

    Attributes:
        content: Conteúdo sucinto, preservado sem conversão ou interpretação.
        source_task_id: Identificador da tarefa que originou o aprendizado, ou `None` quando ele
            vem do enunciado (A.3) e portanto não pertence a nenhuma tarefa.
    """

    content: str
    source_task_id: str | None = None
