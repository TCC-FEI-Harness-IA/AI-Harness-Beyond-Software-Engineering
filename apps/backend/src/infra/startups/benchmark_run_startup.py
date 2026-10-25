from inspect import getfile
from typing import AsyncGenerator

from src.application.dtos.run_benchmark_input_dto import RunBenchmarkInputDTO
from src.application.usecases.run_benchmark_usecase import RunBenchmarkUseCase
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.benchmark_answer_evaluator import BenchmarkAnswerEvaluator
from src.infra.adapters.benchmark_flow_runner_adapter import BenchmarkFlowRunnerAdapter
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.adapters.id_generator_adapter import IdGeneratorAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO
from src.infra.routes.v1.benchmark.dtos.benchmark_run_input_dto import BenchmarkRunInputDTO

_PROGRESS_FRAME_TYPE = "progress"
_RESULT_FRAME_TYPE = "result"


class BenchmarkRunStartup:
    """Composition root da execução de uma bateria de benchmark.

    É instanciado uma vez por conexão WebSocket, porque o caso de uso carrega o estado da
    bateria em execução.
    """

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da execução da bateria."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.clock = ClockAdapter()
        self.document_mapper = BenchmarkSessionDocumentMapper()
        self.repository = BenchmarkSessionRepositoryFactory(
            settings=self.settings,
            mapper=self.document_mapper,
        ).create()
        self.question_provider = FileBenchmarkQuestionProvider(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(FileBenchmarkQuestionProvider)),
        )
        self.flow_runner = BenchmarkFlowRunnerAdapter(
            evaluator=BenchmarkAnswerEvaluator(),
            clock=self.clock,
            logger=self.settings.logger(module_file=getfile(BenchmarkFlowRunnerAdapter)),
        )
        self.run_benchmark_use_case = RunBenchmarkUseCase(
            question_provider=self.question_provider,
            flow_runner=self.flow_runner,
            repository=self.repository,
            clock=self.clock,
            id_generator=IdGeneratorAdapter(settings=self.settings),
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(RunBenchmarkUseCase)),
        )
        self.logger.info("BenchmarkRunStartup inicializado")

    async def run(self, payload: BenchmarkRunInputDTO) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        """Executa a bateria a partir do frame de abertura do WebSocket.

        Args:
            payload: Frame de abertura no contrato de transporte.

        Yields:
            BenchmarkFrameDTO: Um frame `progress` por mudança de estado e um `result` final.
        """
        input_dto = RunBenchmarkInputDTO(
            question_count=payload.question_count,
            max_parallel=payload.max_parallel,
            model_name=payload.llm_model_config.provider_config.model_name,
            max_tokens=payload.llm_model_config.max_tokens,
            temperature=payload.llm_model_config.temperature,
            provider=payload.llm_model_config.provider,
        )
        async for benchmark_session in self.run_benchmark_use_case.execute(input_dto=input_dto):
            is_running = benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING
            yield BenchmarkFrameDTO(
                type=_PROGRESS_FRAME_TYPE if is_running else _RESULT_FRAME_TYPE,
                benchmark_session=self.document_mapper.to_document(benchmark_session=benchmark_session),
            )
