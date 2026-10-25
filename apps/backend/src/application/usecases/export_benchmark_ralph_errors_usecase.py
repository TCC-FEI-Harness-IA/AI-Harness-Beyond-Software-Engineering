import logging

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.session_repository_interface import ISessionRepository


class ExportBenchmarkRalphErrorsUseCase:
    """Reúne as questões erradas no Ralph Loop de uma bateria encerrada, sem executar nada de novo."""

    def __init__(
        self,
        benchmark_repository: IBenchmarkSessionRepository,
        session_repository: ISessionRepository,
        question_provider: IBenchmarkQuestionProvider,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            benchmark_repository: Repositório das baterias de benchmark.
            session_repository: Repositório das sessões geradas pelos fluxos.
            question_provider: Fonte do enunciado e das alternativas das questões.
            logger: Logger do módulo.
        """
        self.benchmark_repository: IBenchmarkSessionRepository = benchmark_repository
        self.session_repository: ISessionRepository = session_repository
        self.question_provider: IBenchmarkQuestionProvider = question_provider
        self.logger = logger

    async def execute(self, benchmark_session_id: str) -> list[BenchmarkRalphError]:
        """Lista as questões com desfecho incorreto no Ralph Loop, na ordem da bateria.

        Falhas técnicas e respostas inválidas contam como erro, como nos totais da bateria.
        Questões certas, sem desfecho do Ralph Loop e o fluxo simples ficam de fora.

        Args:
            benchmark_session_id: Identificador da bateria.

        Returns:
            list[BenchmarkRalphError]: Erros do Ralph Loop, nunca vazia.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            BenchmarkSessionNotFinishedError: Quando a bateria ainda está em execução.
            NoBenchmarkErrorsToExportError: Quando nenhuma questão errou no Ralph Loop.
        """
        self.logger.info("Reunindo os erros do Ralph Loop da bateria '%s'", benchmark_session_id)
        benchmark_session = await self.benchmark_repository.find_by_id(benchmark_session_id=benchmark_session_id)
        if benchmark_session is None:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session_id)
        if benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)

        dataset = {question.id: question for question in self.question_provider.list_questions()}
        errors: list[BenchmarkRalphError] = []
        for run in benchmark_session.questions:
            outcome = run.ralph
            if outcome is None or outcome.is_correct:
                continue
            session = (
                await self.session_repository.find_by_id(session_id=outcome.session_id)
                if outcome.session_id is not None
                else None
            )
            errors.append(
                BenchmarkRalphError(
                    question_id=run.question_id,
                    expected_alternative=run.expected_alternative,
                    outcome=outcome,
                    question=dataset.get(run.question_id),
                    session=session,
                )
            )

        if not errors:
            raise NoBenchmarkErrorsToExportError(benchmark_session_id=benchmark_session_id)
        return errors
