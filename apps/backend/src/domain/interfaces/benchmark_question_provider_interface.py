from abc import ABC, abstractmethod

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion


class IBenchmarkQuestionProvider(ABC):
    """Contrato de acesso ao dataset de questões do benchmark."""

    @abstractmethod
    def list_questions(self) -> list[BenchmarkQuestion]:
        """Devolve todas as questões válidas, em ordem determinística.

        Returns:
            list[BenchmarkQuestion]: Questões do dataset, ordenadas pelo identificador.
        """
        raise NotImplementedError

    @abstractmethod
    def answer_instruction(self) -> str:
        """Devolve a instrução de resposta anexada ao enunciado de cada questão.

        Returns:
            str: Instrução comum aos dois fluxos.
        """
        raise NotImplementedError
