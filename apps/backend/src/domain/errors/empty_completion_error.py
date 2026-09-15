from src.domain.errors.ralph_error import RalphError

_LENGTH_FINISH_REASON = "length"
_LENGTH_HINT = (
    " O motivo de término foi 'length': o teto de tokens de saída acabou antes de o modelo "
    "escrever a resposta. Em modelos de raciocínio isso acontece quando o raciocínio interno "
    "consome todo o orçamento — aumente 'max_tokens' ou limite o esforço de raciocínio em "
    "LLM_REASONING_EFFORT."
)


class EmptyCompletionError(RalphError):
    """Levantado quando o provedor responde sem nenhum texto utilizável.

    Uma completion vazia não é uma resposta: se ela seguisse adiante, o fluxo
    baseline devolveria uma resposta em branco ao usuário e o fluxo harness
    acusaria uma falha de parsing genérica, escondendo a causa real.

    Attributes:
        finish_reason: Motivo de término informado pelo provedor, quando há.
    """

    def __init__(self, finish_reason: str | None) -> None:
        """Inicializa o erro.

        Args:
            finish_reason: Motivo de término informado pelo provedor, quando há.
        """
        self.finish_reason = finish_reason
        hint = _LENGTH_HINT if finish_reason == _LENGTH_FINISH_REASON else ""
        super().__init__(
            f"O provedor devolveu uma resposta sem conteúdo de texto. "
            f"Motivo de término: '{finish_reason}'.{hint}"
        )
