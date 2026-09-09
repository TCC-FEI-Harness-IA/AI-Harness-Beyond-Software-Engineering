import logging

from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.settings_interface import ISettings


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
        """
        raise NotImplementedError

    async def record_user_input(self, content: str) -> SessionMessage:
        """Registra a pergunta do usuário no histórico da sessão.

        Args:
            content: Conteúdo da pergunta do usuário.

        Returns:
            SessionMessage: Mensagem registrada.
        """
        raise NotImplementedError

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
        """
        raise NotImplementedError

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
        """
        raise NotImplementedError

    async def record_degradation(self, degradation: SessionDegradation) -> None:
        """Registra uma degradação ocorrida durante a sessão.

        Args:
            degradation: Degradação a ser registrada.
        """
        raise NotImplementedError

    async def finish(self, status: SessionStatusEnum, final_answer: str | None) -> Session:
        """Encerra e persiste a sessão com o status e a resposta final informados.

        Args:
            status: Estado final da sessão.
            final_answer: Resposta final entregue ao usuário, quando houver.

        Returns:
            Session: Sessão encerrada.
        """
        raise NotImplementedError

    @property
    def session(self) -> Session:
        """Sessão atualmente rastreada pelo recorder.

        Returns:
            Session: Sessão em andamento.
        """
        raise NotImplementedError
