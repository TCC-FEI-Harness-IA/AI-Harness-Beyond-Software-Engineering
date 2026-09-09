import logging

from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.message_source_enum import MessageSourceEnum
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
    ) -> None:
        """Inicializa o adapter.

        Args:
            repository: Repositório de persistência de sessões.
            clock: Fonte de tempo do domínio.
            id_generator: Gerador de identificadores de sessão e mensagem.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.repository: ISessionRepository = repository
        self.clock: IClock = clock
        self.id_generator: IIdGenerator = id_generator
        self.settings: ISettings = settings
        self.logger = logger
        self.__session: Session | None = None
        self.__wall_time_start_ms: int = _NO_INFERENCE_TIME_MS

    async def start(
        self,
        user_question: str,
        flow: ThinkingPhaseEnum,
        model_name: str,
        max_tokens: int,
        temperature: float,
    ) -> Session:
        """Inicia e persiste uma nova sessão.

        Args:
            user_question: Pergunta original enviada pelo usuário.
            flow: Fluxo usado pela sessão.
            model_name: Nome do modelo usado na sessão.
            max_tokens: Limite de tokens de saída configurado para a sessão.
            temperature: Temperatura de geração configurada para a sessão.

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
        )

    async def record_llm_message(
        self,
        phase: ThinkingPhaseEnum,
        content: str,
        tokens: TokensUsage,
        inference_time_ms: int,
        task_id: str | None,
        context_id: str | None,
    ) -> SessionMessage:
        """Registra o resultado de uma chamada ao modelo no histórico da sessão.

        Args:
            phase: Fase de thinking que produziu a mensagem.
            content: Conteúdo produzido pelo modelo.
            tokens: Consumo de tokens da chamada.
            inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.

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
        )

    async def record_programmatic_step(
        self,
        phase: ThinkingPhaseEnum,
        content: str,
        task_id: str | None,
        context_id: str | None,
    ) -> SessionMessage:
        """Registra uma etapa programática (sem chamada ao modelo) no histórico.

        Args:
            phase: Fase de thinking que produziu a etapa.
            content: Conteúdo da etapa.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.

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
        )

    async def record_degradation(self, degradation: SessionDegradation) -> None:
        """Registra uma degradação ocorrida durante a sessão.

        Args:
            degradation: Degradação a ser registrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada.
        """
        session = self.session
        session.register_degradation(degradation=degradation)
        self.logger.info("Degradação '%s' registrada na sessão '%s'", degradation.limit.value, session.id)
        await self.repository.save(session=session)

    async def finish(self, status: SessionStatusEnum, final_answer: str | None) -> Session:
        """Encerra e persiste a sessão com o status e a resposta final informados.

        Args:
            status: Estado final da sessão.
            final_answer: Resposta final entregue ao usuário, quando houver.

        Returns:
            Session: Sessão encerrada.

        Raises:
            ValueError: Quando a sessão ainda não foi iniciada ou já foi encerrada.
        """
        session = self.session
        session.totals.wall_time_ms = self.clock.monotonic_ms() - self.__wall_time_start_ms
        session.finish(status=status, final_answer=final_answer)

        await self.repository.save(session=session)
        self.logger.info("Sessão '%s' encerrada com status '%s'", session.id, status.value)
        return session

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
        )
        session.add_message(message=message)

        if self.settings.ralph_session_flush_every_message:
            await self.repository.save(session=session)

        return message
