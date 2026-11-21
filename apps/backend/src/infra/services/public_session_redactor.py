import re
from typing import Any

PLACEHOLDER = "[conteúdo omitido: os autores do dataset pedem que as questões não sejam publicadas em texto]"

# Só valores estruturais sobrevivem: identificadores, fases, subtipos, estados e datas. Todo texto
# livre (pergunta, prompts, saídas, justificativas) é omitido.
_KEPT_KEYS = frozenset({
    "_id", "id", "flow", "model_name", "status", "created_at", "updated_at", "provider", "phase", "source",
    "task_id", "context_id", "timestamp", "subtype", "started_at", "outcome", "finish_reason",
    "provider_response_id", "invocation_id", "recovers_invocation_id", "inference_mode", "run_id",
    "question_name", "expected_alternative", "selected_alternative", "reason", "occurred_at", "kind",
    "revising_task_id", "verdict", "code", "defect", "result", "syntax_status", "resolved_by_invocation_id",
})
_STRUCTURAL_VALUE = re.compile(r"^[A-Za-z0-9_.:+/-]{0,80}$")


class PublicSessionRedactor:
    """Omite o texto de sessões públicas de datasets protegidos, preservando a estrutura.

    A análise pública do Ralph usa só fases, subtipos, tarefas e totais, que continuam intactos.
    """

    def redact(self, document: Any, key: str | None = None) -> Any:
        """Cópia do documento com todo texto livre substituído.

        Args:
            document: Documento (ou fragmento) da sessão.
            key: Chave do fragmento no objeto pai.

        Returns:
            Any: Fragmento com os textos omitidos.
        """
        if isinstance(document, dict):
            return {item: self.redact(value, key=item) for item, value in document.items()}
        if isinstance(document, list):
            return [self.redact(value, key=key) for value in document]
        if isinstance(document, str):
            if key in _KEPT_KEYS and _STRUCTURAL_VALUE.fullmatch(document):
                return document
            return PLACEHOLDER if document else document
        return document
