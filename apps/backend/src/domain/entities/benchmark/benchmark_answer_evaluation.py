from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkAnswerEvaluation:
    """Resultado determinístico da avaliação de uma resposta do benchmark.

    Attributes:
        selected_alternative: Letra identificada na resposta, ou `None`.
        is_correct: Acerto; falhas técnicas e respostas inválidas contam como erro.
        error: Diagnóstico da falha técnica ou da resposta inválida, quando houve.
    """

    selected_alternative: str | None
    is_correct: bool
    error: str | None
