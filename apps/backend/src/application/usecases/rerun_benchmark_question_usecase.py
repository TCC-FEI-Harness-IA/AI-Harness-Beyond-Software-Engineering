import asyncio
import copy
import logging
from collections import deque
from collections.abc import Callable
from contextlib import aclosing
from typing import AsyncGenerator, ClassVar

from src.application.dtos.rerun_benchmark_question_output_dto import RerunBenchmarkQuestionOutputDTO
from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
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
    """Reexecuta os fluxos errados (ou com falha) de questões de uma bateria já encerrada.

    Serve para conferir se uma correção no código resolveu uma questão que antes quebrava: o fluxo
    errado roda de novo com a mesma configuração de modelo da bateria, numa sessão nova, e o novo
    desfecho substitui o anterior na bateria. Fluxos que já acertaram não são refeitos.

    A bateria é persistida a cada desfecho substituído, nunca no meio de um fluxo; se o consumidor
    para de ler (cliente desconectado), o fluxo em andamento é cancelado e o desfecho anterior
    permanece. Só um lote por bateria roda por vez dentro do processo; as questões do lote
    respeitam o paralelismo da bateria e os fluxos de cada questão continuam em sequência.
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
        """Reexecuta uma questão pelo mesmo executor de lotes."""
        async with aclosing(self.execute_many(benchmark_session_id, [question_id])) as updates:
            async for update in updates:
                yield update

    async def execute_many(
        self, benchmark_session_id: str, question_ids: list[str]
    ) -> AsyncGenerator[RerunBenchmarkQuestionOutputDTO, None]:
        """Valida todo o lote antes de executar e emite o estado até o último `finished`.

        Recusa baterias inexistentes ou ainda em execução, listas vazias ou repetidas e questões
        que não pertencem à bateria/dataset ou não têm fluxos errados para refazer.
        """
        if not question_ids or len(set(question_ids)) != len(question_ids):
            raise InvalidBenchmarkRequestError("Selecione ao menos uma questão, sem identificadores repetidos.")
        if benchmark_session_id in self._active_sessions:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)
        self._active_sessions.add(benchmark_session_id)
        try:
            benchmark_session = await self.__load(benchmark_session_id=benchmark_session_id)
            provider, queue = self.__prepare(benchmark_session=benchmark_session, question_ids=question_ids)
            self.logger.info(
                "Reexecutando %s questões da bateria '%s'",
                len(question_ids),
                benchmark_session_id,
            )

            changed = asyncio.Event()
            task = asyncio.create_task(
                self.__run_workers(
                    benchmark_session=benchmark_session,
                    provider=provider,
                    queue=queue,
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
                for question_id in question_ids:
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

    def __prepare(
        self, benchmark_session: BenchmarkSession, question_ids: list[str]
    ) -> tuple[IBenchmarkQuestionProvider, deque[tuple[BenchmarkQuestion, list[BenchmarkInferenceModeEnum]]]]:
        """Resolve o dataset uma vez e valida todas as questões antes de iniciar qualquer fluxo."""
        runs = {question.question_id: question for question in benchmark_session.questions}
        for question_id in question_ids:
            if question_id not in runs:
                raise InvalidBenchmarkRequestError(
                    f"A questão '{question_id}' não pertence à bateria '{benchmark_session.id}'."
                )
        provider = self.question_provider_for(benchmark_session.benchmark)
        if provider.definition().revision != benchmark_session.benchmark.revision:
            raise InvalidBenchmarkRequestError(
                f"A revisão do dataset ('{benchmark_session.benchmark.revision}') da bateria "
                f"'{benchmark_session.id}' não está mais disponível."
            )
        if provider.definition().split != benchmark_session.benchmark.split:
            raise InvalidBenchmarkRequestError("Subconjunto da bateria indisponível para reexecução.")
        questions = {question.id: question for question in provider.list_questions()}
        queue = deque()
        for question_id in question_ids:
            if question_id not in questions:
                raise InvalidBenchmarkRequestError(f"A questão '{question_id}' não existe mais no dataset da bateria.")
            modes = [mode for mode in self._FLOW_ORDER if mode in runs[question_id].rerunnable_modes]
            if not modes:
                raise BenchmarkQuestionNotRerunnableError(benchmark_session.id, question_id)
            queue.append((questions[question_id], modes))
        return provider, queue

    # ── Execução ─────────────────────────────────────────────────────────────

    async def __run_workers(
        self,
        benchmark_session: BenchmarkSession,
        provider: IBenchmarkQuestionProvider,
        queue: deque[tuple[BenchmarkQuestion, list[BenchmarkInferenceModeEnum]]],
        changed: asyncio.Event,
    ) -> None:
        """Consome a fila com paralelismo limitado e cancela todos os workers se um deles falhar."""
        save_lock = asyncio.Lock()

        async def work() -> None:
            while queue:
                question, modes = queue.popleft()
                await self.__rerun(benchmark_session, provider, question, modes, changed, save_lock)

        workers = [asyncio.create_task(work()) for _ in range(min(benchmark_session.max_parallel, len(queue)))]
        try:
            await asyncio.gather(*workers)
        finally:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    async def __rerun(
        self,
        benchmark_session: BenchmarkSession,
        provider: IBenchmarkQuestionProvider,
        question: BenchmarkQuestion,
        modes: list[BenchmarkInferenceModeEnum],
        changed: asyncio.Event,
        save_lock: asyncio.Lock,
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
            await self.__record_outcome(benchmark_session, question.id, outcome, save_lock)
            changed.set()

    async def __record_outcome(
        self,
        benchmark_session: BenchmarkSession,
        question_id: str,
        outcome: BenchmarkFlowOutcome,
        save_lock: asyncio.Lock,
    ) -> None:
        """Serializa gravações e persiste só desfechos, sem o progresso transitório dos outros workers."""
        async with save_lock:
            at = self.clock.now()
            snapshot = copy.deepcopy(benchmark_session)
            snapshot.record_rerun_outcome(question_id=question_id, outcome=outcome, at=at)
            for question in snapshot.questions:
                question.abort_rerun()
            await self.repository.save(benchmark_session=snapshot)
            benchmark_session.record_rerun_outcome(question_id=question_id, outcome=outcome, at=at)

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
