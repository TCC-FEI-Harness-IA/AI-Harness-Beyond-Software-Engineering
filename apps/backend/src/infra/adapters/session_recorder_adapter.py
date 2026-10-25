import logging

from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session import Session
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.settings_interface import ISettings

_NO_TOKENS = 0
_NO_INFERENCE_TIME_MS = 0
_FIRST_MESSAGE_ORDER = 0


class SessionRecorderAdapter(ISessionRecorder):
    """Adapter de `ISessionRecorder` que persiste a sessão via `ISessionRepository`."""

    def __init__(
        self,
        repository: ISessionRepository,
        clock: IClock,
        id_generator: IIdGenerator,
        settings: ISettings,
        logger: logging.Logger,
        benchmark_details: BenchmarkDetails | None = None,
    ) -> None:
        """Inicializa o adapter.

        Args:
            repository: Repositório de persistência de sessões.
            clock: Fonte de tempo do domínio.
            id_generator: Gerador de identificadores de sessão e mensagem.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
            benchmark_details: Metadados opcionais, persistidos desde a criação da sessão.
        """
        self.repository: ISessionRepository = repository
        self.clock: IClock = clock
        self.id_generator: IIdGenerator = id_generator
        self.settings: ISettings = settings
        self.logger = logger
        self.benchmark_details = benchmark_details or BenchmarkDetails()
        self.__session: Session | None = None
        self.__wall_time_start_ms: int = _NO_INFERENCE_TIME_MS

    async def start(
        self,
        user_question: str,
        flow: ThinkingPhaseEnum,
        model_name: str,
        max_tokens: int,
        temperature: float,
        provider: ModelProviderEnum | None = None,
    ) -> Session:
        """Inicia e persiste uma nova sessão.

        Args:
            user_question: Pergunta original enviada pelo usuário.
            flow: Fluxo usado pela sessão.
            model_name: Nome do modelo usado na sessão.
            max_tokens: Limite de tokens de saída configurado para a sessão.
            temperature: Temperatura de geração configurada para a sessão.
            provider: Provedor efetivo das chamadas da sessão, quando conhecido.

        Returns:
            Session: Sessão recém-criada.

        Raises:
            ValueError: Quando a sessão já foi iniciada.
        """
        if self.__session is not None:
            raise ValueError(f"Sessão '{self.__session.id}' já foi iniciada por este recorder.")

        created_at = self.clock.now()
        self.__session = Session(
            id=self.id_generator.new_session_id(),
            user_question=user_question,
            flow=flow,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            status=SessionStatusEnum.RUNNING,
            created_at=created_at,
            updated_at=created_at,
            provider=provider,
            benchmark_details=self.benchmark_details,
        )
        self.__wall_time_start_ms = self.clock.monotonic_ms()

        await self.repository.save(session=self.__session)
        self.logger.info("Sessão '%s' iniciada", self.__session.id)
        return self.__session

    async def record_user_input(self, content: str) -> SessionMessage:
        """Registra a pergunta do usuário no histórico da sessão.

        Args:
            content: Conteúdo da pergunta do usuário.

        Returns:
            SessionMessage: Mensagem registrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        return await self.__record(
            phase=self.session.flow,
            source=MessageSourceEnum.USER,
            content=content,
            task_id=None,
            context_id=None,
            tokens_input=_NO_TOKENS,
            tokens_output=_NO_TOKENS,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
            model_name=None,
            prompt_input=(),
        )

    async def record_llm_message(
        self,
        phase: ThinkingPhaseEnum,
        content: str,
        tokens: TokensUsage,
        inference_time_ms: int,
        task_id: str | None,
        context_id: str | None,
        prompt_input: tuple[Message, ...],
    ) -> SessionMessage:
        """Registra o resultado de uma chamada ao modelo no histórico da sessão.

        Args:
            phase: Fase de thinking que produziu a mensagem.
            content: Conteúdo produzido pelo modelo.
            tokens: Consumo de tokens da chamada.
            inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.
            prompt_input: Conversa enviada ao modelo na chamada que produziu `content`.

        Returns:
            SessionMessage: Mensagem registrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        return await self.__record(
            phase=phase,
            source=MessageSourceEnum.LLM_AGENT,
            content=content,
            task_id=task_id,
            context_id=context_id,
            tokens_input=tokens.tokens_input,
            tokens_output=tokens.tokens_output,
            inference_time_ms=inference_time_ms,
            model_name=tokens.llm_model.model_name,
            prompt_input=prompt_input,
        )

    async def record_programmatic_step(
        self,
        phase: ThinkingPhaseEnum,
        content: str,
        task_id: str | None,
        context_id: str | None,
        prompt_input: tuple[Message, ...] = (),
    ) -> SessionMessage:
        """Registra uma etapa programática (sem chamada ao modelo) no histórico.

        Args:
            phase: Fase de thinking que produziu a etapa.
            content: Conteúdo da etapa.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.
            prompt_input: Conversa enviada ao modelo, quando a etapa registra a saída de uma chamada
                (como uma saída descartada pelo parser); vazia nas demais etapas.

        Returns:
            SessionMessage: Mensagem registrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        return await self.__record(
            phase=phase,
            source=MessageSourceEnum.SYSTEM,
            content=content,
            task_id=task_id,
            context_id=context_id,
            tokens_input=_NO_TOKENS,
            tokens_output=_NO_TOKENS,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
            model_name=None,
            prompt_input=prompt_input,
        )

    async def start_invocation(
        self,
        phase: ThinkingPhaseEnum,
        task_id: str | None,
        context_id: str | None,
        model_name: str,
        provider: ModelProviderEnum,
        temperature: float | None = None,
    ) -> str:
        """Registra o envio de uma chamada ao modelo, que já conta nos totais da sessão.

        Args:
            phase: Fase de thinking que faz a chamada.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.
            model_name: Modelo solicitado.
            provider: Provedor que atende a chamada.
            temperature: Temperatura efetivamente pedida na chamada.

        Returns:
            str: Identificador da invocação, para `complete_invocation`.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        session = self.session
        invocation = LLMInvocation(
            id=self.id_generator.new_invocation_id(),
            phase=phase,
            task_id=task_id,
            context_id=context_id,
            model_name=model_name,
            provider=provider,
            started_at=self.clock.now(),
            temperature=temperature,
        )
        session.start_invocation(invocation=invocation)
        await self.__flush(session=session)
        return invocation.id

    async def complete_invocation(
        self,
        invocation_id: str,
        outcome: InvocationOutcomeEnum,
        duration_ms: int,
        tokens_input: int | None,
        tokens_output: int | None,
        finish_reason: str | None = None,
        provider_response_id: str | None = None,
    ) -> None:
        """Conclui uma invocação registrada, acumulando o seu consumo conhecido nos totais.

        Args:
            invocation_id: Identificador devolvido por `start_invocation`.
            outcome: Desfecho da chamada.
            duration_ms: Duração da chamada, em milissegundos.
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            finish_reason: Motivo de término informado pelo provedor, quando há.
            provider_response_id: Identificador da resposta no provedor, quando há.

        Raises:
            ValueError: Quando a sessão não foi iniciada ou a invocação não pode ser concluída.
        """
        session = self.session
        session.complete_invocation(
            invocation_id=invocation_id,
            outcome=outcome,
            duration_ms=duration_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            finish_reason=finish_reason,
            provider_response_id=provider_response_id,
        )
        await self.__flush(session=session)

    async def finish(
        self,
        status: SessionStatusEnum,
        final_answer: str | None,
        failure: SessionFailure | None = None,
    ) -> Session:
        """Encerra e persiste a sessão com o status e a resposta final informados.

        Args:
            status: Estado final da sessão.
            final_answer: Resposta final entregue ao usuário, quando houver.
            failure: Motivo estruturado do encerramento sem conclusão, quando houver.

        Returns:
            Session: Sessão encerrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada ou já foi encerrada.
            Exception: A falha do repositório, quando a gravação do encerramento não conclui. A sessão
                volta a ficar em execução, porque só vale como encerrada o que foi persistido; assim o
                chamador ainda pode encerrá-la por outro caminho.
        """
        session = self.session
        previous_updated_at = session.updated_at
        previous_wall_time_ms = session.totals.wall_time_ms
        session.finish(status=status, final_answer=final_answer, failure=failure)
        session.totals.wall_time_ms = self.clock.monotonic_ms() - self.__wall_time_start_ms

        try:
            await self.repository.save(session=session)
        except Exception:
            session.reopen(updated_at=previous_updated_at)
            session.totals.wall_time_ms = previous_wall_time_ms
            self.logger.exception("Falha ao persistir o encerramento da sessão '%s'", session.id)
            raise
        self.logger.info("Sessão '%s' encerrada com status '%s'", session.id, status.value)
        return session

    async def update_benchmark_details(self, details: BenchmarkDetails) -> None:
        """Persiste a avaliação sem modificar mensagens, status ou métricas da inferência."""
        session = self.session
        previous = session.benchmark_details
        session.benchmark_details = details
        try:
            await self.repository.save(session=session)
        except Exception:
            session.benchmark_details = previous
            raise

    @property
    def session(self) -> Session:
        """Sessão atualmente rastreada pelo recorder.

        Returns:
            Session: Sessão em andamento.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        if self.__session is None:
            raise ValueError("A sessão não foi iniciada: chame 'start' antes de qualquer registro.")
        return self.__session

    async def __record(
        self,
        phase: ThinkingPhaseEnum,
        source: MessageSourceEnum,
        content: str,
        task_id: str | None,
        context_id: str | None,
        tokens_input: int,
        tokens_output: int,
        inference_time_ms: int,
        model_name: str | None,
        prompt_input: tuple[Message, ...],
    ) -> SessionMessage:
        """Monta, anexa e persiste uma mensagem no histórico da sessão corrente.

        A ordem é sequencial a partir de zero, o identificador vem do gerador
        injetado e o instante vem do relógio injetado. A persistência só ocorre
        aqui quando `RALPH_SESSION_FLUSH_EVERY_MESSAGE` está ligado.

        Returns:
            SessionMessage: Mensagem registrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        session = self.session
        message = SessionMessage(
            id=self.id_generator.new_message_id(),
            order=_FIRST_MESSAGE_ORDER + len(session.messages),
            timestamp=self.clock.now(),
            phase=phase,
            source=source,
            content=content,
            task_id=task_id,
            context_id=context_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            inference_time_ms=inference_time_ms,
            model_name=model_name,
            prompt_input=tuple(prompt_input),
        )
        session.add_message(message=message)
        await self.__flush(session=session)

        return message

    async def __flush(self, session: Session) -> None:
        """Persiste a sessão quando `RALPH_SESSION_FLUSH_EVERY_MESSAGE` está ligado.

        Args:
            session: Sessão em andamento.
        """
        if self.settings.ralph_session_flush_every_message:
            await self.repository.save(session=session)
