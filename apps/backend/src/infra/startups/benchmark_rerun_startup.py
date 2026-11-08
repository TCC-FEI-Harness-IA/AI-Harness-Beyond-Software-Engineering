from contextlib import aclosing
from inspect import getfile
from typing import AsyncGenerator

from src.application.usecases.rerun_benchmark_question_usecase import RerunBenchmarkQuestionUseCase
from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.benchmark_answer_evaluator import BenchmarkAnswerEvaluator
from src.infra.adapters.benchmark_flow_runner_adapter import BenchmarkFlowRunnerAdapter
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.providers.benchmark_question_provider_factory import BenchmarkQuestionProviderFactory
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO

_PROGRESS_FRAME_TYPE = "progress"
_RESULT_FRAME_TYPE = "result"


class BenchmarkRerunStartup:
    """Composition root da reexecução de questões de uma bateria de benchmark.

    É instanciado uma vez por conexão WebSocket, como o da execução da bateria.
    """

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da reexecução."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.clock = ClockAdapter()
        self.document_mapper = BenchmarkSessionDocumentMapper()
        self.repository = BenchmarkSessionRepositoryFactory(
            settings=self.settings,
            mapper=self.document_mapper,
        ).create()
        self.provider_factory = BenchmarkQuestionProviderFactory(self.settings, self.logger)
        self.flow_runner = BenchmarkFlowRunnerAdapter(
            evaluator=BenchmarkAnswerEvaluator(),
            clock=self.clock,
            logger=self.settings.logger(module_file=getfile(BenchmarkFlowRunnerAdapter)),
        )
        self.rerun_use_case = RerunBenchmarkQuestionUseCase(
            question_provider_for=self.__provider_for,
            flow_runner=self.flow_runner,
            repository=self.repository,
            clock=self.clock,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(RerunBenchmarkQuestionUseCase)),
        )
        self.logger.info("BenchmarkRerunStartup inicializado")

    def __provider_for(self, definition: BenchmarkDefinition) -> IBenchmarkQuestionProvider:
        """Dataset e protocolo (few-shot) com que a bateria foi executada."""
        return self.provider_factory.for_definition(definition)

    async def run(self, benchmark_session_id: str, question_id: str) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        """Preserva o endpoint de reexecução individual."""
        async with aclosing(self.run_many(benchmark_session_id, [question_id])) as frames:
            async for frame in frames:
                yield frame

    async def run_many(
        self, benchmark_session_id: str, question_ids: list[str]
    ) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        """Reexecuta o lote emitindo `progress` e um `result` final; fechar cancela todos os workers."""
        async with aclosing(self.rerun_use_case.execute_many(benchmark_session_id, question_ids)) as updates:
            async for update in updates:
                yield BenchmarkFrameDTO(
                    type=_RESULT_FRAME_TYPE if update.finished else _PROGRESS_FRAME_TYPE,
                    benchmark_session=self.document_mapper.to_document(benchmark_session=update.benchmark_session),
                )
