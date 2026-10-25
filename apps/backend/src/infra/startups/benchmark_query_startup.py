from inspect import getfile
from typing import Any

from src.application.usecases.get_benchmark_session_usecase import GetBenchmarkSessionUseCase
from src.application.usecases.list_benchmark_sessions_usecase import ListBenchmarkSessionsUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory


class BenchmarkQueryStartup:
    """Composition root das consultas de benchmark: baterias persistidas e dataset de questões."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências das consultas."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.document_mapper = BenchmarkSessionDocumentMapper()
        self.repository = BenchmarkSessionRepositoryFactory(
            settings=self.settings,
            mapper=self.document_mapper,
        ).create()
        self.question_provider = FileBenchmarkQuestionProvider(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(FileBenchmarkQuestionProvider)),
        )
        self.get_benchmark_session_use_case = GetBenchmarkSessionUseCase(
            repository=self.repository,
            logger=self.settings.logger(module_file=getfile(GetBenchmarkSessionUseCase)),
        )
        self.list_benchmark_sessions_use_case = ListBenchmarkSessionsUseCase(
            repository=self.repository,
            logger=self.settings.logger(module_file=getfile(ListBenchmarkSessionsUseCase)),
        )
        self.logger.info("BenchmarkQueryStartup inicializado")

    async def get_benchmark_session_document(self, benchmark_session_id: str) -> dict[str, Any]:
        """Consulta uma bateria e devolve o documento que a representa.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            dict[str, Any]: Documento da bateria, serializável em JSON.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            ValueError: Quando o identificador ou o documento persistido é inválido.
        """
        benchmark_session = await self.get_benchmark_session_use_case.execute(
            benchmark_session_id=benchmark_session_id
        )
        return self.document_mapper.to_document(benchmark_session=benchmark_session)

    async def list_benchmark_session_documents(self) -> list[dict[str, Any]]:
        """Lista os documentos de todas as baterias, da mais recente para a mais antiga.

        Returns:
            list[dict[str, Any]]: Documentos das baterias.
        """
        benchmark_sessions = await self.list_benchmark_sessions_use_case.execute()
        return [self.document_mapper.to_document(benchmark_session=item) for item in benchmark_sessions]

    def describe_dataset(self) -> dict[str, Any]:
        """Descreve o dataset e os limites aceitos para uma nova bateria.

        Returns:
            dict[str, Any]: Identificadores das questões, na ordem de execução, e os limites de paralelismo
            e de `max_tokens` aceitos numa bateria.

        Raises:
            ValueError: Quando o dataset é inválido.
        """
        return {
            "question_ids": [question.id for question in self.question_provider.list_questions()],
            "max_parallel_limit": self.settings.ralph_benchmark_max_parallel,
            "max_tokens_limit": self.settings.ralph_benchmark_max_tokens_limit,
        }
