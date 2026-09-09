import logging

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO
from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.session_recorder_interface import ISessionRecorder

_NO_TOKENS = 0


class DefaultMessageUseCase:
    """Fluxo baseline do experimento: uma única chamada direta ao modelo.

    É o grupo de controle da comparação com o harness: não há planejamento,
    loop de execução nem validação de critérios de aceite. Ainda assim a sessão
    é gravada por inteiro, com histórico, consumo de tokens e tempo de
    inferência, para que os dois fluxos sejam comparáveis nos benchmarks.
    """

    def __init__(
        self,
        llm_completions: ILLMCompletions,
        session_recorder: ISessionRecorder,
        clock: IClock,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            llm_completions: Porta de completions do domínio.
            session_recorder: Rastreio e persistência da sessão.
            clock: Fonte de tempo, usada para medir o tempo de inferência.
            logger: Logger do módulo.
        """
        self.llm_completions: ILLMCompletions = llm_completions
        self.session_recorder: ISessionRecorder = session_recorder
        self.clock: IClock = clock
        self.logger = logger

    async def execute(self, user_input: DefaultMessageInputDTO) -> DefaultMessageOutputDTO:
        """Executa uma inferência direta, grava a sessão e devolve as métricas.

        Args:
            user_input: Pergunta do usuário e parâmetros do modelo.

        Returns:
            DefaultMessageOutputDTO: Resposta do modelo, sessão gravada e consumo da chamada.

        Raises:
            ValueError: Quando o provedor não devolve resultado.
        """
        self.logger.info("Iniciando execução de DefaultMessageUseCase")

        session = await self.session_recorder.start(
            user_question=user_input.user_input,
            flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
            model_name=user_input.model_name,
            max_tokens=user_input.max_tokens,
            temperature=user_input.temperature,
        )
        await self.session_recorder.record_user_input(content=user_input.user_input)

        try:
            llm_response, inference_time_ms = await self.__infer(user_input=user_input)
        except Exception:
            self.logger.exception("Erro ao executar DefaultMessageUseCase")
            await self.session_recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None)
            raise

        response_text = self.__extract_output_text(llm_response=llm_response)
        tokens = self.__resolve_tokens(llm_response=llm_response, model_name=user_input.model_name)

        await self.session_recorder.record_llm_message(
            phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
            content=response_text,
            tokens=tokens,
            inference_time_ms=inference_time_ms,
            task_id=None,
            context_id=None,
        )
        await self.session_recorder.finish(
            status=SessionStatusEnum.COMPLETED,
            final_answer=response_text,
        )

        return DefaultMessageOutputDTO(
            message=user_input.user_input,
            response=response_text,
            session_id=session.id,
            tokens_input=tokens.tokens_input,
            tokens_output=tokens.tokens_output,
            inference_time_ms=inference_time_ms,
        )

    async def __infer(self, user_input: DefaultMessageInputDTO) -> tuple[LLMMessage, int]:
        """Chama o modelo cronometrando a inferência.

        Args:
            user_input: Pergunta do usuário e parâmetros do modelo.

        Returns:
            tuple[LLMMessage, int]: Resultado da chamada e sua duração em milissegundos.

        Raises:
            ValueError: Quando o provedor não devolve resultado.
        """
        input_message = Message(
            creation_timestamp=self.clock.now(),
            text=user_input.user_input,
            source=MessageSourceEnum.USER,
        )

        started_at_ms = self.clock.monotonic_ms()
        llm_response = await self.llm_completions.send_message(
            input_message=input_message,
            model_name=user_input.model_name,
            max_tokens=user_input.max_tokens,
            temperature=user_input.temperature,
        )
        inference_time_ms = self.clock.monotonic_ms() - started_at_ms

        if llm_response is None:
            raise ValueError("Resposta do LLM veio como None.")

        return llm_response, inference_time_ms

    def __extract_output_text(self, llm_response: LLMMessage) -> str:
        """Extrai o texto da mensagem de saída, ou vazio quando ela não existe.

        Args:
            llm_response: Resultado devolvido pela porta de completions.

        Returns:
            str: Texto produzido pelo modelo.
        """
        if llm_response.output_message is None:
            return ""
        return llm_response.output_message.text

    def __resolve_tokens(self, llm_response: LLMMessage, model_name: str) -> TokensUsage:
        """Devolve o consumo da chamada, ou um consumo zerado quando o provedor o omite.

        Args:
            llm_response: Resultado devolvido pela porta de completions.
            model_name: Modelo pedido na requisição, usado no consumo zerado.

        Returns:
            TokensUsage: Consumo de tokens a ser contabilizado na sessão.
        """
        if llm_response.tokens is not None:
            return llm_response.tokens

        return TokensUsage(
            tokens_input=_NO_TOKENS,
            tokens_output=_NO_TOKENS,
            llm_model=GenaiModel(model_name=model_name, model_provider=ModelProviderEnum.OPEN_ROUTER),
        )
