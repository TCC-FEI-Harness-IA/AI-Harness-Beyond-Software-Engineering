import asyncio
import logging
from collections.abc import Callable
from typing import AsyncGenerator, ClassVar

from src.application.dtos.rerun_benchmark_question_output_dto import RerunBenchmarkQuestionOutputDTO
from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_question_not_rerunnable_error import BenchmarkQuestionNotRerunnableError
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.interfaces.benchmark_flow_runner_interface import IBenchmarkFlowRunner
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.settings_interface import ISettings


class RerunBenchmarkQuestionUseCase:
    """Reexecuta os fluxos errados (ou com falha) de uma questão de uma bateria já encerrada.

    Serve para conferir se uma correção no código resolveu uma questão que antes quebrava: o fluxo
    errado roda de novo com a mesma configuração de modelo da bateria, numa sessão nova, e o novo
    desfecho substitui o anterior na bateria. Fluxos que já acertaram não são refeitos.

    A bateria é persistida a cada desfecho substituído, nunca no meio de um fluxo; se o consumidor
    para de ler (cliente desconectado), o fluxo em andamento é cancelado e o desfecho anterior
    permanece. Só uma reexecução por bateria roda por vez dentro do processo.
    """

    _active_sessions: ClassVar[set[str]] = set()
    _FLOW_ORDER = (BenchmarkInferenceModeEnum.SIMPLE, BenchmarkInferenceModeEnum.RALPH)

    def __init__(
        self,
        question_provider_for: Callable[[BenchmarkDefinition], IBenchmarkQuestionProvider],
        flow_runner: IBenchmarkFlowRunner,
        repository: IBenchmarkSessionRepository,
        clock: IClock,
        settings: ISettings,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            question_provider_for: Resolve o dataset de questões a partir da definição da bateria.
            flow_runner: Executor dos fluxos simples e Ralph.
            repository: Persistência das baterias.
            clock: Fonte de tempo.
            settings: Configurações, fonte do intervalo de progresso.
            logger: Logger do módulo.
        """
        self.question_provider_for = question_provider_for
        self.flow_runner: IBenchmarkFlowRunner = flow_runner
        self.repository: IBenchmarkSessionRepository = repository
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger

    async def execute(
        self, benchmark_session_id: str, question_id: str
    ) -> AsyncGenerator[RerunBenchmarkQuestionOutputDTO, None]:
        """Reexecuta a questão, emitindo o estado da bateria a cada mudança.

        Args:
            benchmark_session_id: Bateria que contém a questão.
            question_id: Questão reexecutada.

        Yields:
            RerunBenchmarkQuestionOutputDTO: Estado da bateria; o último emitido tem `finished`.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
            BenchmarkSessionNotFinishedError: Quando a bateria, ou uma reexecução dela, ainda está em execução.
            InvalidBenchmarkRequestError: Quando a questão não pertence à bateria ou ao dataset.
            BenchmarkQuestionNotRerunnableError: Quando a questão não tem fluxo errado para refazer.
        """
        if benchmark_session_id in self._active_sessions:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)
        self._active_sessions.add(benchmark_session_id)
        try:
            benchmark_session = await self.__load(benchmark_session_id=benchmark_session_id)
            provider, question = self.__find_question(benchmark_session=benchmark_session, question_id=question_id)
            rerunnable = benchmark_session.question(question_id).rerunnable_modes
            modes = [mode for mode in self._FLOW_ORDER if mode in rerunnable]
            if not modes:
                raise BenchmarkQuestionNotRerunnableError(
                    benchmark_session_id=benchmark_session_id, question_id=question_id
                )
            self.logger.info(
                "Reexecutando a questão '%s' da bateria '%s' nos fluxos %s",
                question_id,
                benchmark_session_id,
                [mode.value for mode in modes],
            )

            changed = asyncio.Event()
            task = asyncio.create_task(
                self.__rerun(
                    benchmark_session=benchmark_session,
                    provider=provider,
                    question=question,
                    modes=modes,
                    changed=changed,
                )
            )
            try:
                yield RerunBenchmarkQuestionOutputDTO(benchmark_session=benchmark_session, finished=False)
                while not task.done():
                    await self.__wait_for_change(changed=changed, task=task)
                    if not task.done():
                        yield RerunBenchmarkQuestionOutputDTO(benchmark_session=benchmark_session, finished=False)
                task.result()
            finally:
                await self.__stop(task=task)
                benchmark_session.question(question_id).abort_rerun()
            yield RerunBenchmarkQuestionOutputDTO(benchmark_session=benchmark_session, finished=True)
        finally:
            self._active_sessions.discard(benchmark_session_id)

    # ── Preparação ───────────────────────────────────────────────────────────

    async def __load(self, benchmark_session_id: str) -> BenchmarkSession:
        """Busca a bateria e recusa uma que ainda esteja em execução."""
        benchmark_session = await self.repository.find_by_id(benchmark_session_id=benchmark_session_id)
        if benchmark_session is None:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session_id)
        if benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)
        return benchmark_session

    def __find_question(
        self, benchmark_session: BenchmarkSession, question_id: str
    ) -> tuple[IBenchmarkQuestionProvider, BenchmarkQuestion]:
        """Localiza a questão no dataset da bateria, depois de conferir que ela pertence à bateria."""
        try:
            benchmark_session.question(question_id)
        except ValueError as error:
            raise InvalidBenchmarkRequestError(str(error)) from error
        provider = self.question_provider_for(benchmark_session.benchmark)
        if provider.definition().revision != benchmark_session.benchmark.revision:
            raise InvalidBenchmarkRequestError(
                f"A revisão do dataset ('{benchmark_session.benchmark.revision}') da bateria "
                f"'{benchmark_session.id}' não está mais disponível."
            )
        for question in provider.list_questions():
            if question.id == question_id:
                return provider, question
        raise InvalidBenchmarkRequestError(f"A questão '{question_id}' não existe mais no dataset da bateria.")

    # ── Execução ─────────────────────────────────────────────────────────────

    async def __rerun(
        self,
        benchmark_session: BenchmarkSession,
        provider: IBenchmarkQuestionProvider,
        question: BenchmarkQuestion,
        modes: list[BenchmarkInferenceModeEnum],
        changed: asyncio.Event,
    ) -> None:
        """Refaz cada fluxo errado, em sequência, persistindo a bateria a cada desfecho."""
        prompt = provider.build_prompt(question=question, instruction=provider.answer_instruction().strip())
        for mode in modes:
            benchmark_session.start_rerun(question_id=question.id, mode=mode, at=self.clock.now())
            changed.set()

            def on_tokens(total_tokens: int) -> None:
                benchmark_session.track_tokens(question_id=question.id, total_tokens=total_tokens)
                changed.set()

            outcome = await self.flow_runner.run(
                request=BenchmarkFlowRequest(
                    question=question,
                    mode=mode,
                    prompt=prompt,
                    llm_config=benchmark_session.llm_config,
                    benchmark_session_id=benchmark_session.id,
                ),
                on_tokens=on_tokens,
            )
            benchmark_session.record_rerun_outcome(question_id=question.id, outcome=outcome, at=self.clock.now())
            await self.repository.save(benchmark_session=benchmark_session)
            changed.set()

    async def __wait_for_change(self, changed: asyncio.Event, task: asyncio.Future) -> None:
        """Espera uma mudança, o fim da reexecução ou o intervalo de progresso, o que vier primeiro."""
        waiter = asyncio.ensure_future(changed.wait())
        try:
            await asyncio.wait(
                {waiter, task},
                timeout=self.settings.ralph_benchmark_progress_interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            waiter.cancel()
        changed.clear()

    @staticmethod
    async def __stop(task: asyncio.Task) -> None:
        """Cancela a reexecução ainda ativa e espera que termine."""
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
