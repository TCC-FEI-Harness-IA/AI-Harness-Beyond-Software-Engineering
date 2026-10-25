import asyncio
import logging
from collections import deque
from typing import AsyncGenerator

from src.application.dtos.run_benchmark_input_dto import RunBenchmarkInputDTO
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.benchmark.benchmark_llm_config import BenchmarkLLMConfig
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.interfaces.benchmark_flow_runner_interface import IBenchmarkFlowRunner
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.settings_interface import ISettings

_FLOW_ORDER = (BenchmarkInferenceModeEnum.SIMPLE, BenchmarkInferenceModeEnum.RALPH)
_MIN_PARALLEL = 1
_MIN_QUESTIONS = 1
_MIN_TOKENS = 1


class RunBenchmarkUseCase:
    """Executa uma bateria de benchmark e emite o seu estado a cada mudança.

    As questões entram numa fila FIFO, na ordem do dataset, consumida por até `max_parallel`
    workers. Cada worker executa a questão inteira em sequência: inferência simples e depois o
    Ralph Loop, cada um na própria sessão. O estado da bateria é emitido quando uma questão ou
    um fluxo começa ou termina, quando o consumo de tokens muda e, sem mudanças, a cada
    `ralph_benchmark_progress_interval_seconds`, para que o tempo decorrido siga atualizado.

    A bateria é persistida no início, a cada desfecho de fluxo e no encerramento. Se o consumidor
    para de ler (cliente desconectado), os workers são cancelados e a bateria é encerrada como
    `interrupted`; uma falha técnica da bateria a encerra como `failed`.
    """

    def __init__(
        self,
        question_provider: IBenchmarkQuestionProvider,
        flow_runner: IBenchmarkFlowRunner,
        repository: IBenchmarkSessionRepository,
        clock: IClock,
        id_generator: IIdGenerator,
        settings: ISettings,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            question_provider: Dataset de questões e instrução de resposta.
            flow_runner: Executor dos fluxos simples e Ralph.
            repository: Persistência das baterias.
            clock: Fonte de tempo.
            id_generator: Gerador do identificador da bateria.
            settings: Configurações, fonte do limite de paralelismo e do intervalo de progresso.
            logger: Logger do módulo.
        """
        self.question_provider: IBenchmarkQuestionProvider = question_provider
        self.flow_runner: IBenchmarkFlowRunner = flow_runner
        self.repository: IBenchmarkSessionRepository = repository
        self.clock: IClock = clock
        self.id_generator: IIdGenerator = id_generator
        self.settings: ISettings = settings
        self.logger = logger
        self.__save_lock = asyncio.Lock()
        self.__started_at_ms = 0

    async def execute(self, input_dto: RunBenchmarkInputDTO) -> AsyncGenerator[BenchmarkSession, None]:
        """Executa a bateria, emitindo o estado atual a cada mudança e o estado final ao terminar.

        Args:
            input_dto: Quantidade de questões, paralelismo e configuração do modelo.

        Yields:
            BenchmarkSession: Estado da bateria; o último emitido já está encerrado.

        Raises:
            InvalidBenchmarkRequestError: Antes de criar a bateria, quando os parâmetros não podem ser atendidos
                (`max_tokens`, `max_parallel` ou `question_count` fora do permitido).
        """
        questions = self.__select_questions(input_dto=input_dto)
        instruction = self.question_provider.answer_instruction().strip()
        benchmark_session = self.__new_session(input_dto=input_dto, questions=questions)
        self.__started_at_ms = self.clock.monotonic_ms()
        await self.__persist(benchmark_session)
        self.logger.info(
            "Bateria '%s' iniciada com %d questões e até %d em paralelo",
            benchmark_session.id,
            benchmark_session.question_count,
            benchmark_session.max_parallel,
        )

        changed = asyncio.Event()
        queue: deque[BenchmarkQuestion] = deque(questions)
        workers = [
            asyncio.create_task(self.__work(benchmark_session, queue, instruction, changed))
            for _ in range(min(benchmark_session.max_parallel, len(questions)))
        ]
        all_workers = asyncio.gather(*workers)

        try:
            yield self.__refresh(benchmark_session)
            while not all_workers.done():
                await self.__wait_for_change(changed=changed, all_workers=all_workers)
                if not all_workers.done():
                    yield self.__refresh(benchmark_session)
            all_workers.result()
            await self.__finish(benchmark_session, BenchmarkSessionStatusEnum.COMPLETED)
        except Exception as error:
            self.logger.exception("Falha na bateria '%s'", benchmark_session.id)
            await self.__stop(workers=workers, all_workers=all_workers)
            await self.__finish(benchmark_session, BenchmarkSessionStatusEnum.FAILED, error=str(error))
        finally:
            if benchmark_session.status is BenchmarkSessionStatusEnum.RUNNING:
                self.logger.info("Bateria '%s' interrompida antes de terminar", benchmark_session.id)
                await self.__stop(workers=workers, all_workers=all_workers)
                await self.__finish(benchmark_session, BenchmarkSessionStatusEnum.INTERRUPTED)

        yield benchmark_session

    # ── Preparação ───────────────────────────────────────────────────────────

    def __select_questions(self, input_dto: RunBenchmarkInputDTO) -> list[BenchmarkQuestion]:
        """Valida os parâmetros e escolhe as primeiras questões do dataset.

        Raises:
            InvalidBenchmarkRequestError: Quando `max_tokens`, o paralelismo ou a quantidade de questões
                estão fora do permitido.
        """
        max_tokens_limit = self.settings.ralph_benchmark_max_tokens_limit
        if not _MIN_TOKENS <= input_dto.max_tokens <= max_tokens_limit:
            raise InvalidBenchmarkRequestError(
                f"max_tokens deve estar entre {_MIN_TOKENS} e {max_tokens_limit}. Valor: {input_dto.max_tokens}. "
                "Cada chamada do Ralph reserva max_tokens no orçamento da sessão, e a inferência simples não "
                "cabe na janela de contexto do modelo acima disso."
            )
        max_parallel_limit = self.settings.ralph_benchmark_max_parallel
        if not _MIN_PARALLEL <= input_dto.max_parallel <= max_parallel_limit:
            raise InvalidBenchmarkRequestError(
                f"max_parallel deve estar entre {_MIN_PARALLEL} e {max_parallel_limit}. "
                f"Valor: {input_dto.max_parallel}."
            )

        questions = self.question_provider.list_questions()
        if input_dto.question_count is None:
            return questions
        if not _MIN_QUESTIONS <= input_dto.question_count <= len(questions):
            raise InvalidBenchmarkRequestError(
                f"question_count deve estar entre {_MIN_QUESTIONS} e {len(questions)}. "
                f"Valor: {input_dto.question_count}."
            )
        return questions[: input_dto.question_count]

    def __new_session(self, input_dto: RunBenchmarkInputDTO, questions: list[BenchmarkQuestion]) -> BenchmarkSession:
        """Cria a bateria com todas as questões pendentes."""
        created_at = self.clock.now()
        return BenchmarkSession(
            id=self.id_generator.new_benchmark_session_id(),
            llm_config=BenchmarkLLMConfig(
                model_name=input_dto.model_name,
                provider=input_dto.provider,
                max_tokens=input_dto.max_tokens,
                temperature=input_dto.temperature,
            ),
            max_parallel=input_dto.max_parallel,
            status=BenchmarkSessionStatusEnum.RUNNING,
            created_at=created_at,
            updated_at=created_at,
            questions=[
                BenchmarkQuestionRun(question_id=question.id, expected_alternative=question.expected_alternative)
                for question in questions
            ],
        )

    # ── Execução ─────────────────────────────────────────────────────────────

    async def __work(
        self,
        benchmark_session: BenchmarkSession,
        queue: deque[BenchmarkQuestion],
        instruction: str,
        changed: asyncio.Event,
    ) -> None:
        """Worker: consome a fila e executa cada questão nos dois fluxos, em sequência."""
        while queue:
            question = queue.popleft()
            prompt = f"{question.statement}\n\n{instruction}"
            for mode in _FLOW_ORDER:
                benchmark_session.start_flow(question_id=question.id, mode=mode, at=self.clock.now())
                changed.set()

                def on_tokens(total_tokens: int, question_id: str = question.id) -> None:
                    benchmark_session.track_tokens(question_id=question_id, total_tokens=total_tokens)
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
                benchmark_session.record_outcome(question_id=question.id, outcome=outcome, at=self.clock.now())
                if mode is _FLOW_ORDER[-1]:
                    benchmark_session.finish_question(question_id=question.id, at=self.clock.now())
                await self.__persist(benchmark_session)
                changed.set()

    async def __wait_for_change(self, changed: asyncio.Event, all_workers: asyncio.Future) -> None:
        """Espera uma mudança, o fim dos workers ou o intervalo de progresso, o que vier primeiro."""
        waiter = asyncio.ensure_future(changed.wait())
        try:
            await asyncio.wait(
                {waiter, all_workers},
                timeout=self.settings.ralph_benchmark_progress_interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            waiter.cancel()
        changed.clear()

    async def __stop(self, workers: list[asyncio.Task], all_workers: asyncio.Future) -> None:
        """Cancela os workers ainda ativos e espera que terminem."""
        all_workers.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    # ── Estado e persistência ────────────────────────────────────────────────

    def __refresh(self, benchmark_session: BenchmarkSession) -> BenchmarkSession:
        """Atualiza o tempo decorrido antes de emitir o estado."""
        benchmark_session.update_wall_time(wall_time_ms=self.__elapsed_ms())
        return benchmark_session

    async def __finish(
        self,
        benchmark_session: BenchmarkSession,
        status: BenchmarkSessionStatusEnum,
        error: str | None = None,
    ) -> None:
        """Encerra e persiste a bateria.

        A falha de persistência no encerramento é registrada no log e não substitui o desfecho:
        o estado final ainda é entregue ao consumidor.
        """
        benchmark_session.finish(status=status, at=self.clock.now(), wall_time_ms=self.__elapsed_ms(), error=error)
        try:
            await self.__persist(benchmark_session)
        except Exception:
            self.logger.exception("Não foi possível persistir o encerramento da bateria '%s'", benchmark_session.id)
        self.logger.info("Bateria '%s' encerrada com status '%s'", benchmark_session.id, status.value)

    async def __persist(self, benchmark_session: BenchmarkSession) -> None:
        """Grava a bateria, serializando as gravações concorrentes dos workers."""
        async with self.__save_lock:
            await self.repository.save(benchmark_session=benchmark_session)

    def __elapsed_ms(self) -> int:
        """Tempo decorrido desde o início da bateria, em milissegundos."""
        return self.clock.monotonic_ms() - self.__started_at_ms
