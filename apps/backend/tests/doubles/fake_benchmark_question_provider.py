from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider


class FakeBenchmarkQuestionProvider(IBenchmarkQuestionProvider):
    """Dublê de `IBenchmarkQuestionProvider` com questões e instrução em memória."""

    def __init__(self, questions: list[BenchmarkQuestion], instruction: str = "Instrução comum") -> None:
        """Configura o dublê.

        Args:
            questions: Questões devolvidas, na ordem.
            instruction: Instrução de resposta devolvida.
        """
        self.questions = list(questions)
        self.instruction = instruction

    def list_questions(self) -> list[BenchmarkQuestion]:
        """Devolve uma cópia das questões configuradas."""
        return list(self.questions)

    def answer_instruction(self) -> str:
        """Devolve a instrução configurada."""
        return self.instruction
