import logging
from collections.abc import Callable

from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.session_repository_interface import ISessionRepository


class ExportBenchmarkSessionUseCase:
    """Reúne uma bateria encerrada com tudo que está atrelado a ela, sem executar nada de novo.

    Para cada questão: a execução registrada na bateria, o enunciado original e o gabarito do
    dataset e as sessões completas da inferência simples e do Ralph Loop.
    """

    def __init__(
        self,
        benchmark_repository: IBenchmarkSessionRepository,
        session_repository: ISessionRepository,
        question_provider_for: Callable[[BenchmarkDefinition], IBenchmarkQuestionProvider],
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            benchmark_repository: Repositório das baterias de benchmark.
            session_repository: Repositório das sessões geradas pelos fluxos.
            question_provider_for: Fonte das questões do dataset da bateria.
            logger: Logger do módulo.
        """
        self.benchmark_repository: IBenchmarkSessionRepository = benchmark_repository
        self.session_repository: ISessionRepository = session_repository
        self.question_provider_for = question_provider_for
        self.logger = logger

    async def execute(self, benchmark_session_id: str) -> BenchmarkSessionBundle:
        """Monta o pacote completo da bateria, na ordem das questões.

        Questões que o dataset atual não conhece (ou de uma revisão diferente da bateria) e
        sessões que não existem mais ficam como `None`, sem impedir a exportação.

        Args:
            benchmark_session_id: Identificador da bateria.

        Returns:
            BenchmarkSessionBundle: Bateria com o conteúdo de cada questão.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            BenchmarkSessionNotFinishedError: Quando a bateria ainda está em execução.
        """
        self.logger.info("Exportando a bateria completa '%s'", benchmark_session_id)
        benchmark_session = await self.benchmark_repository.find_by_id(benchmark_session_id=benchmark_session_id)
        if benchmark_session is None:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session_id)
        if benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)

        dataset = self.__dataset(benchmark_session=benchmark_session)
        items = [
            BenchmarkSessionBundleItem(
                run=run,
                question=dataset.get(run.question_id),
                simple_session=await self.__session(outcome=run.simple),
                ralph_session=await self.__session(outcome=run.ralph),
            )
            for run in benchmark_session.questions
        ]
        return BenchmarkSessionBundle(benchmark_session=benchmark_session, items=items)

    def __dataset(self, benchmark_session: BenchmarkSession) -> dict[str, BenchmarkQuestion]:
        """Questões do dataset da bateria, ou vazio quando a revisão disponível é outra."""
        definition = benchmark_session.benchmark
        try:
            provider = self.question_provider_for(definition)
            available = provider.definition()
            same_revision = (
                definition.dataset is BenchmarkDatasetEnum.VESTIBULAR or available.revision == definition.revision
            )
            if not same_revision or available.split != definition.split:
                self.logger.warning(
                    "Revisão do dataset difere da bateria '%s'; ela será exportada sem enunciados",
                    benchmark_session.id,
                )
                return {}
            return {question.id: question for question in provider.list_questions()}
        except Exception:
            self.logger.warning(
                "Dataset '%s' indisponível; a bateria '%s' será exportada sem enunciados",
                definition.dataset.value,
                benchmark_session.id,
                exc_info=True,
            )
            return {}

    async def __session(self, outcome: BenchmarkFlowOutcome | None) -> Session | None:
        """Sessão persistida pelo fluxo, quando ele chegou a criá-la e ela ainda existe."""
        if outcome is None or outcome.session_id is None:
            return None
        return await self.session_repository.find_by_id(session_id=outcome.session_id)
