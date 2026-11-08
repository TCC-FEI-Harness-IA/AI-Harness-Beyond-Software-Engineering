import re

from src.domain.entities.benchmark.benchmark_answer_evaluation import BenchmarkAnswerEvaluation
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion

# Marcador da última linha no idioma de cada benchmark: vestibulares em português, MMLU e GPQA em inglês.
_FINAL_MARKERS = ("RESPOSTA_FINAL", "FINAL_ANSWER")
_FINAL_PATTERN = re.compile(rf"^({'|'.join(_FINAL_MARKERS)}):\s*([A-E])\s*$", re.MULTILINE)
_BOLD_MARKUP = "**"
_INVALID_ANSWER = "Resposta sem alternativa final válida e inequívoca."


class BenchmarkAnswerEvaluator:
    """Avaliação determinística das respostas do benchmark.

    Lê a última linha `RESPOSTA_FINAL: LETRA` (ou `FINAL_ANSWER: LETTER`), uma letra isolada ou uma
    alternativa completa isolada. Respostas ambíguas, sem alternativa e falhas técnicas contam como erro, com
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
        if any(f"{marker}:" in clean for marker in _FINAL_MARKERS):
            matches = _FINAL_PATTERN.findall(clean)
            last_line = clean.splitlines()[-1].strip()
            if len(matches) == 1 and last_line == f"{matches[0][0]}: {matches[0][1]}":
                return matches[0][1]
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
        if selected not in question.options:
            return BenchmarkAnswerEvaluation(selected_alternative=None, is_correct=False, error=_INVALID_ANSWER)
        return BenchmarkAnswerEvaluation(
            selected_alternative=selected,
            is_correct=selected == question.expected_alternative,
            error=None,
        )
