import logging

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_import_conflict_error import BenchmarkSessionImportConflictError
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.session_repository_interface import ISessionRepository


class ImportBenchmarkSessionUseCase:
    """Persiste uma bateria exportada, com todas as suas sessões, sem sobrescrever nada.

    As sessões são gravadas antes da bateria, para que ela só apareça na listagem quando tudo
    que ela referencia já existe. Se a gravação falhar no meio, as sessões já gravadas são
    removidas.
    """

    def __init__(
        self,
        benchmark_repository: IBenchmarkSessionRepository,
        session_repository: ISessionRepository,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            benchmark_repository: Repositório das baterias de benchmark.
            session_repository: Repositório das sessões geradas pelos fluxos.
            logger: Logger do módulo.
        """
        self.benchmark_repository: IBenchmarkSessionRepository = benchmark_repository
        self.session_repository: ISessionRepository = session_repository
        self.logger = logger

    async def execute(self, bundle: BenchmarkSessionBundle) -> BenchmarkSession:
        """Valida e grava a bateria e as suas sessões.

        Args:
            bundle: Bateria lida do arquivo exportado.

        Returns:
            BenchmarkSession: Bateria importada.

        Raises:
            InvalidBenchmarkArchiveError: Quando a bateria está em execução ou o pacote é
                inconsistente (questões ou sessões que não correspondem à bateria).
            BenchmarkSessionImportConflictError: Quando a bateria ou alguma sessão já existe.
        """
        benchmark_session = bundle.benchmark_session
        self.logger.info("Importando a bateria '%s'", benchmark_session.id)
        self.__validate(bundle=bundle)

        conflicts: list[str] = []
        if await self.benchmark_repository.find_by_id(benchmark_session_id=benchmark_session.id) is not None:
            conflicts.append(benchmark_session.id)
        for session in bundle.sessions:
            if await self.session_repository.find_by_id(session_id=session.id) is not None:
                conflicts.append(session.id)
        if conflicts:
            raise BenchmarkSessionImportConflictError(
                benchmark_session_id=benchmark_session.id, conflicting_ids=conflicts
            )

        saved: list[str] = []
        try:
            for session in bundle.sessions:
                await self.session_repository.save(session=session)
                saved.append(session.id)
            await self.benchmark_repository.save(benchmark_session=benchmark_session)
        except Exception:
            await self.__rollback(saved_session_ids=saved)
            raise

        self.logger.info(
            "Bateria '%s' importada com %d sessões", benchmark_session.id, len(saved)
        )
        return benchmark_session

    def __validate(self, bundle: BenchmarkSessionBundle) -> None:
        """Confere que o pacote descreve uma bateria encerrada e coerente consigo mesma.

        Raises:
            InvalidBenchmarkArchiveError: Na primeira inconsistência encontrada.
        """
        benchmark_session = bundle.benchmark_session
        if benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING:
            raise InvalidBenchmarkArchiveError("a bateria está marcada como em execução.")

        run_ids = [run.question_id for run in benchmark_session.questions]
        item_ids = [item.run.question_id for item in bundle.items]
        if run_ids != item_ids:
            raise InvalidBenchmarkArchiveError("as questões do pacote não correspondem às da bateria.")

        for run, item in zip(benchmark_session.questions, bundle.items, strict=True):
            for label, outcome, session in (
                ("simples", run.simple, item.simple_session),
                ("Ralph Loop", run.ralph, item.ralph_session),
            ):
                if session is None:
                    continue
                if outcome is None or outcome.session_id != session.id:
                    raise InvalidBenchmarkArchiveError(
                        f"a sessão '{session.id}' do fluxo {label} da questão '{run.question_id}' "
                        "não é a registrada na bateria."
                    )

        session_ids = [session.id for session in bundle.sessions]
        if len(session_ids) != len(set(session_ids)):
            raise InvalidBenchmarkArchiveError("o pacote repete a mesma sessão em mais de um fluxo.")

    async def __rollback(self, saved_session_ids: list[str]) -> None:
        """Remove as sessões gravadas por uma importação que falhou no meio."""
        for session_id in saved_session_ids:
            try:
                await self.session_repository.delete(session_id=session_id)
            except Exception:
                self.logger.exception("Não foi possível desfazer a importação da sessão '%s'", session_id)
