import asyncio
import logging
from collections.abc import Callable
from contextlib import aclosing
from dataclasses import replace
from typing import Any

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.interfaces.benchmark_flow_runner_interface import IBenchmarkFlowRunner
from src.domain.interfaces.clock_interface import IClock
from src.domain.services.benchmark_answer_evaluator import BenchmarkAnswerEvaluator
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

_RESULT_EVENT_TYPE = "result"
_ERROR_EVENT_TYPE = "error"
_MILLISECONDS_PER_SECOND = 1000
_NO_TOKENS = 0
_RALPH_WITHOUT_ANSWER = "O RALPH terminou sem emitir uma resposta final."


class BenchmarkFlowRunnerAdapter(IBenchmarkFlowRunner):
    """Executa os fluxos do benchmark pelos mesmos composition roots usados pela API.

    Cada fluxo cria o próprio startup (`DefaultMessageStartup` ou `RalphThinkingStartup`), e por isso
    a própria sessão, persistida no repositório normal e identificada desde a criação pelos
    metadados de benchmark. Ao terminar, a avaliação é gravada na mesma sessão. Se a bateria é
    cancelada no meio de um fluxo, a sessão em execução é encerrada como `failed`, como faz o
    WebSocket do Ralph quando o cliente desconecta.
    """

    def __init__(
        self,
        evaluator: BenchmarkAnswerEvaluator,
        clock: IClock,
        logger: logging.Logger,
        simple_startup_factory: Callable[..., Any] = DefaultMessageStartup,
        ralph_startup_factory: Callable[..., Any] = RalphThinkingStartup,
    ) -> None:
        """Inicializa o adapter.

        Args:
            evaluator: Avaliação determinística das respostas.
            clock: Fonte de tempo, usada para medir a duração dos fluxos.
            logger: Logger do módulo.
            simple_startup_factory: Fábrica do composition root da inferência simples.
            ralph_startup_factory: Fábrica do composition root do Ralph Loop.
        """
        self.evaluator = evaluator
        self.clock: IClock = clock
        self.logger = logger
        self.simple_startup_factory = simple_startup_factory
        self.ralph_startup_factory = ralph_startup_factory

    async def run(self, request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        """Executa o fluxo, avalia a resposta e grava a avaliação na sessão do fluxo.

        Args:
            request: Questão, fluxo, prompt e configuração do modelo.
            on_tokens: Chamado com o consumo acumulado do Ralph a cada evento.

        Returns:
            BenchmarkFlowOutcome: Desfecho avaliado; falhas do fluxo viram `error`, nunca exceção.
        """
        details = self.__initial_details(request=request)
        started_at_ms = self.clock.monotonic_ms()
        if request.mode is BenchmarkInferenceModeEnum.SIMPLE:
            startup = self.simple_startup_factory(benchmark_details=details)
            recorder: SessionRecorderAdapter = startup.default_message_use_case.session_recorder
            response, error = await self.__guard(recorder, self.__run_simple(startup=startup, request=request))
        else:
            startup = self.ralph_startup_factory(benchmark_details=details)
            recorder = startup.session_recorder
            response, error = await self.__guard(
                recorder, self.__run_ralph(startup=startup, request=request, on_tokens=on_tokens)
            )

        evaluation = self.evaluator.evaluate(question=request.question, response=response, error=error)
        session = self.__session(recorder=recorder)
        outcome = BenchmarkFlowOutcome(
            mode=request.mode,
            session_id=session.id if session is not None else None,
            selected_alternative=evaluation.selected_alternative,
            is_correct=evaluation.is_correct,
            error=evaluation.error,
            duration_seconds=(self.clock.monotonic_ms() - started_at_ms) / _MILLISECONDS_PER_SECOND,
            total_tokens=session.totals.total_tokens if session is not None else _NO_TOKENS,
        )
        return await self.__record_evaluation(recorder=recorder, response=response, outcome=outcome)

    # ── Fluxos ───────────────────────────────────────────────────────────────

    async def __run_simple(self, startup: Any, request: BenchmarkFlowRequest) -> tuple[str, str | None]:
        """Executa a mesma inferência simples da API."""
        try:
            result = await startup.run(payload=DefaultInputDTO.model_validate(self.__payload(request=request)))
        except Exception as error:
            return "", f"{type(error).__name__}: {error}"
        return result.response, None

    async def __run_ralph(
        self,
        startup: Any,
        request: BenchmarkFlowRequest,
        on_tokens: Callable[[int], None],
    ) -> tuple[str, str | None]:
        """Consome o Ralph completo e usa apenas o evento terminal `result` como resposta."""
        response = ""
        error: str | None = None
        payload = ReasoningInputDTO.model_validate(self.__payload(request=request))
        try:
            async with aclosing(startup.run(payload=payload)) as events:
                async for event in events:
                    on_tokens(event.total_tokens)
                    if event.type == _RESULT_EVENT_TYPE:
                        response = event.content
                    elif event.type == _ERROR_EVENT_TYPE:
                        error = event.content
        except Exception as exception:
            error = error or f"{type(exception).__name__}: {exception}"
        if not response and error is None:
            error = _RALPH_WITHOUT_ANSWER
        return response, error

    async def __guard(self, recorder: SessionRecorderAdapter, flow: Any) -> tuple[str, str | None]:
        """Executa o fluxo encerrando como `failed` a sessão que um cancelamento deixar em execução."""
        try:
            return await flow
        except asyncio.CancelledError:
            session = self.__session(recorder=recorder)
            if session is not None and session.status is SessionStatusEnum.RUNNING:
                await recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None)
            raise

    # ── Avaliação e metadados ────────────────────────────────────────────────

    async def __record_evaluation(
        self,
        recorder: SessionRecorderAdapter,
        response: str,
        outcome: BenchmarkFlowOutcome,
    ) -> BenchmarkFlowOutcome:
        """Grava a avaliação na sessão do fluxo; uma falha de gravação nunca vira acerto."""
        session = self.__session(recorder=recorder)
        if session is None:
            return outcome
        details = replace(
            session.benchmark_details,
            providade_answer=response or None,
            selected_alternative=outcome.selected_alternative,
            is_correct=outcome.is_correct,
            duration_seconds=outcome.duration_seconds,
            error=outcome.error,
        )
        try:
            await recorder.update_benchmark_details(details)
        except Exception as failure:
            self.logger.exception("Falha ao persistir a avaliação da sessão '%s'", session.id)
            return replace(outcome, is_correct=False, error=f"Falha ao persistir avaliação: {failure}")
        return outcome

    def __initial_details(self, request: BenchmarkFlowRequest) -> BenchmarkDetails:
        """Metadados gravados desde a criação da sessão; o gabarito não entra no prompt."""
        question = request.question
        return BenchmarkDetails(
            is_banchmark=True,
            question_name=question.id,
            corret_answer=question.expected_answer,
            inference_mode=request.mode,
            run_id=request.benchmark_session_id,
            expected_alternative=question.expected_alternative,
        )

    def __payload(self, request: BenchmarkFlowRequest) -> dict[str, Any]:
        """Corpo de transporte comum aos dois fluxos, com a configuração da bateria."""
        config = request.llm_config
        return {
            "message": {"user_input": request.prompt},
            "llm_model_config": {
                "provider": config.provider.value,
                "provider_config": {"model_name": config.model_name},
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            },
        }

    @staticmethod
    def __session(recorder: SessionRecorderAdapter) -> Any:
        """Sessão do fluxo, ou `None` quando ela nem chegou a ser criada."""
        try:
            return recorder.session
        except ValueError:
            return None
