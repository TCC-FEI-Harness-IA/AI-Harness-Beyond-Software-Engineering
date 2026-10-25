from inspect import getfile

from src.application.usecases.export_benchmark_ralph_errors_usecase import ExportBenchmarkRalphErrorsUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.services.benchmark_ralph_errors_archive_builder import (
    BenchmarkArchive,
    BenchmarkRalphErrorsArchiveBuilder,
)


class BenchmarkExportStartup:
    """Composition root da exportação dos erros do Ralph Loop de uma bateria de benchmark."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da exportação."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.session_mapper = SessionDocumentMapper()
        self.export_use_case = ExportBenchmarkRalphErrorsUseCase(
            benchmark_repository=BenchmarkSessionRepositoryFactory(
                settings=self.settings,
                mapper=BenchmarkSessionDocumentMapper(),
            ).create(),
            session_repository=SessionRepositoryFactory(settings=self.settings, mapper=self.session_mapper).create(),
            question_provider=FileBenchmarkQuestionProvider(
                settings=self.settings,
                logger=self.settings.logger(module_file=getfile(FileBenchmarkQuestionProvider)),
            ),
            logger=self.settings.logger(module_file=getfile(ExportBenchmarkRalphErrorsUseCase)),
        )
        self.archive_builder = BenchmarkRalphErrorsArchiveBuilder(session_mapper=self.session_mapper)
        self.logger.info("BenchmarkExportStartup inicializado")

    async def export_ralph_errors(self, benchmark_session_id: str) -> BenchmarkArchive:
        """Gera o ZIP com as questões erradas no Ralph Loop de uma bateria encerrada.

        Args:
            benchmark_session_id: Identificador da bateria.

        Returns:
            BenchmarkArchive: ZIP com uma pasta por questão errada.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            BenchmarkSessionNotFinishedError: Quando a bateria ainda está em execução.
            NoBenchmarkErrorsToExportError: Quando nenhuma questão errou no Ralph Loop.
            ValueError: Quando o identificador ou o dataset é inválido.
        """
        errors = await self.export_use_case.execute(benchmark_session_id=benchmark_session_id)
        return self.archive_builder.build(benchmark_session_id=benchmark_session_id, errors=errors)
