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
    acusaria uma falha de parsing genérica, escondendo a causa real. A chamada, porém,
    foi feita e custou: o consumo informado pelo provedor viaja no erro, para não se perder.

    Attributes:
        finish_reason: Motivo de término informado pelo provedor, quando há.
        tokens_input: Tokens de entrada informados pelo provedor, ou `None` se desconhecidos.
        tokens_output: Tokens de saída informados pelo provedor, ou `None` se desconhecidos.
        response_id: Identificador da resposta no provedor, quando há.
    """

    def __init__(
        self,
        finish_reason: str | None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        response_id: str | None = None,
    ) -> None:
        """Inicializa o erro.

        Args:
            finish_reason: Motivo de término informado pelo provedor, quando há.
            tokens_input: Tokens de entrada informados pelo provedor, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados pelo provedor, ou `None` se desconhecidos.
            response_id: Identificador da resposta no provedor, quando há.
        """
        self.finish_reason = finish_reason
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.response_id = response_id
        hint = _LENGTH_HINT if finish_reason == _LENGTH_FINISH_REASON else ""
        super().__init__(
            f"O provedor devolveu uma resposta sem conteúdo de texto. "
            f"Motivo de término: '{finish_reason}'.{hint}"
        )
