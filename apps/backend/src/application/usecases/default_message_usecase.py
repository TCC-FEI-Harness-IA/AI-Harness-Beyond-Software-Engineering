import logging
from datetime import UTC, datetime

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.interfaces.llm_completions_interface import ILLMCompletions

_INFERENCE_TIME_NOT_MEASURED_MS = 0


class DefaultMessageUseCase:
    """Fluxo baseline do experimento: uma única chamada direta ao modelo.

    É o grupo de controle da comparação com o harness: não há planejamento,
    loop de execução nem validação de critérios de aceite.
    """

    def __init__(self, llm_completions: ILLMCompletions, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            llm_completions: Porta de completions do domínio.
            logger: Logger do módulo.
        """
        self.llm_completions: ILLMCompletions = llm_completions
        self.logger = logger

    async def execute(self, user_input: DefaultMessageInputDTO) -> DefaultMessageOutputDTO:
        """Executa uma inferência direta e devolve a resposta com as métricas.

        Args:
            user_input: Pergunta do usuário e parâmetros do modelo.

        Returns:
            DefaultMessageOutputDTO: Resposta do modelo e consumo da chamada.

        Raises:
            ValueError: Quando o provedor não devolve resultado.
        """
        try:
            self.logger.info("Iniciando execução de DefaultMessageUseCase")

            input_message = Message(
                creation_timestamp=datetime.now(tz=UTC),
                text=user_input.user_input,
                source=MessageSourceEnum.USER,
            )

            llm_response = await self.llm_completions.send_message(
                input_message=input_message,
                model_name=user_input.model_name,
                max_tokens=user_input.max_tokens,
                temperature=user_input.temperature,
            )
            if llm_response is None:
                raise ValueError("Resposta do LLM veio como None.")

            return DefaultMessageOutputDTO(
                message=user_input.user_input,
                response=self.__extract_output_text(llm_response=llm_response),
                tokens_input=llm_response.tokens.tokens_input if llm_response.tokens is not None else 0,
                tokens_output=llm_response.tokens.tokens_output if llm_response.tokens is not None else 0,
                inference_time_ms=_INFERENCE_TIME_NOT_MEASURED_MS,
            )
        except Exception:
            self.logger.exception("Erro ao executar DefaultMessageUseCase")
            raise

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
