from abc import ABC, abstractmethod

from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class ISessionRecorder(ABC):
    """Contrato de rastreio e persistência do histórico de uma sessão."""

    @abstractmethod
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
        """
        raise NotImplementedError

    @abstractmethod
    async def record_user_input(self, content: str) -> SessionMessage:
        """Registra a pergunta do usuário no histórico da sessão.

        Args:
            content: Conteúdo da pergunta do usuário.

        Returns:
            SessionMessage: Mensagem registrada.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        raise NotImplementedError

    @abstractmethod
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

        Deve ser chamado depois da autorização e antes do envio ao provedor.

        Args:
            phase: Fase de thinking que faz a chamada.
            task_id: Tarefa associada, quando houver.
            context_id: Janela de contexto associada, quando houver.
            model_name: Modelo solicitado.
            provider: Provedor que atende a chamada.
            temperature: Temperatura efetivamente pedida na chamada.

        Returns:
            str: Identificador da invocação, para `complete_invocation`.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        raise NotImplementedError

    @abstractmethod
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
            Exception: A falha do repositório, quando a gravação não conclui; a sessão então segue
                em execução e pode ser encerrada por outro caminho.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def session(self) -> Session:
        """Sessão atualmente rastreada pelo recorder.

        Returns:
            Session: Sessão em andamento.
        """
        raise NotImplementedError
