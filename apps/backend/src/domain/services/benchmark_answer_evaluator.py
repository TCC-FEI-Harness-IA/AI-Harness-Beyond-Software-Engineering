import re

from src.domain.entities.benchmark.benchmark_answer_evaluation import BenchmarkAnswerEvaluation
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion

_FINAL_MARKER = "RESPOSTA_FINAL:"
_FINAL_PATTERN = re.compile(r"^RESPOSTA_FINAL:\s*([A-E])\s*$", re.MULTILINE)
_BOLD_MARKUP = "**"
_INVALID_ANSWER = "Resposta sem alternativa final válida e inequívoca."


class BenchmarkAnswerEvaluator:
    """Avaliação determinística das respostas do benchmark.

    Lê a última linha `RESPOSTA_FINAL: LETRA`, uma letra isolada ou uma alternativa completa
    isolada. Respostas ambíguas, sem alternativa e falhas técnicas contam como erro, com
    diagnóstico separado.
    """

    def select_alternative(self, response: str, options: dict[str, str]) -> str | None:
        """Identifica a alternativa escolhida, sem confundir alternativas citadas na resolução.

        Marcadores inválidos, conflitantes ou fora da última linha são recusados.

        Args:
            response: Resposta bruta do fluxo.
            options: Texto de cada alternativa, indexado pela letra.

        Returns:
            str | None: Letra escolhida, ou `None` quando não há escolha inequívoca.
        """
        clean = response.replace(_BOLD_MARKUP, "").strip()
        if _FINAL_MARKER in clean:
            matches = _FINAL_PATTERN.findall(clean)
            last_line = clean.splitlines()[-1].strip()
            if len(matches) == 1 and last_line == f"{_FINAL_MARKER} {matches[0]}":
                return matches[0]
            return None
        if clean in options:
            return clean
        for letter, text in options.items():
            if clean == f"{letter}) {text}":
                return letter
        return None

    def evaluate(self, question: BenchmarkQuestion, response: str, error: str | None) -> BenchmarkAnswerEvaluation:
        """Avalia a resposta de um fluxo contra o gabarito.

        Args:
            question: Questão avaliada.
            response: Resposta bruta do fluxo.
            error: Falha técnica do fluxo, quando houve.

        Returns:
            BenchmarkAnswerEvaluation: Alternativa escolhida, acerto e diagnóstico.
        """
        if error is not None:
            return BenchmarkAnswerEvaluation(selected_alternative=None, is_correct=False, error=error)

        selected = self.select_alternative(response=response, options=question.options)
        if selected is None:
            return BenchmarkAnswerEvaluation(selected_alternative=None, is_correct=False, error=_INVALID_ANSWER)
        return BenchmarkAnswerEvaluation(
            selected_alternative=selected,
            is_correct=selected == question.expected_alternative,
            error=None,
        )
