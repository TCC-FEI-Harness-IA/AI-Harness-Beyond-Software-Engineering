from inspect import getfile
from typing import Any

from src.application.usecases.export_benchmark_ralph_errors_usecase import ExportBenchmarkRalphErrorsUseCase
from src.application.usecases.export_benchmark_session_usecase import ExportBenchmarkSessionUseCase
from src.application.usecases.import_benchmark_session_usecase import ImportBenchmarkSessionUseCase
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.providers.benchmark_question_provider_factory import BenchmarkQuestionProviderFactory
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.services.benchmark_ralph_errors_archive_builder import (
    BenchmarkArchive,
    BenchmarkRalphErrorsArchiveBuilder,
)
from src.infra.services.benchmark_session_archive_codec import BenchmarkSessionArchiveCodec


class BenchmarkExportStartup:
    """Composition root da exportação e importação de baterias de benchmark."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da exportação e da importação."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)
        self.clock: IClock = ClockAdapter()

        self.session_mapper = SessionDocumentMapper()
        self.benchmark_mapper = BenchmarkSessionDocumentMapper()
        benchmark_repository = BenchmarkSessionRepositoryFactory(
            settings=self.settings,
            mapper=self.benchmark_mapper,
        ).create()
        session_repository = SessionRepositoryFactory(settings=self.settings, mapper=self.session_mapper).create()
        question_provider_for = BenchmarkQuestionProviderFactory(self.settings, self.logger).for_definition

        self.export_use_case = ExportBenchmarkRalphErrorsUseCase(
            benchmark_repository=benchmark_repository,
            session_repository=session_repository,
            question_provider=FileBenchmarkQuestionProvider(
                settings=self.settings,
                logger=self.settings.logger(module_file=getfile(FileBenchmarkQuestionProvider)),
            ),
            logger=self.settings.logger(module_file=getfile(ExportBenchmarkRalphErrorsUseCase)),
            question_provider_for=question_provider_for,
        )
        self.archive_builder = BenchmarkRalphErrorsArchiveBuilder(session_mapper=self.session_mapper)

        self.export_session_use_case = ExportBenchmarkSessionUseCase(
            benchmark_repository=benchmark_repository,
            session_repository=session_repository,
            question_provider_for=question_provider_for,
            logger=self.settings.logger(module_file=getfile(ExportBenchmarkSessionUseCase)),
        )
        self.import_session_use_case = ImportBenchmarkSessionUseCase(
            benchmark_repository=benchmark_repository,
            session_repository=session_repository,
            logger=self.settings.logger(module_file=getfile(ImportBenchmarkSessionUseCase)),
        )
        self.session_archive_codec = BenchmarkSessionArchiveCodec(
            benchmark_mapper=self.benchmark_mapper,
            session_mapper=self.session_mapper,
        )
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

    async def export_session(self, benchmark_session_id: str) -> BenchmarkArchive:
        """Gera o ZIP padronizado com a bateria encerrada completa.

        Args:
            benchmark_session_id: Identificador da bateria.

        Returns:
            BenchmarkArchive: ZIP com a bateria e, por questão, enunciado, gabarito e as duas execuções.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            BenchmarkSessionNotFinishedError: Quando a bateria ainda está em execução.
            ValueError: Quando o identificador é inválido.
        """
        bundle = await self.export_session_use_case.execute(benchmark_session_id=benchmark_session_id)
        return self.session_archive_codec.build(bundle=bundle, exported_at=self.clock.now())

    async def import_session(self, content: bytes) -> dict[str, Any]:
        """Importa uma bateria a partir do ZIP gerado por `export_session`.

        Args:
            content: Bytes do ZIP.

        Returns:
            dict[str, Any]: Documento da bateria importada, como na consulta.

        Raises:
            InvalidBenchmarkArchiveError: Quando o ZIP é inválido ou inconsistente.
            BenchmarkSessionImportConflictError: Quando a bateria ou alguma sessão já existe.
        """
        bundle = self.session_archive_codec.read(content=content)
        benchmark_session = await self.import_session_use_case.execute(bundle=bundle)
        return self.benchmark_mapper.to_document(benchmark_session=benchmark_session)
