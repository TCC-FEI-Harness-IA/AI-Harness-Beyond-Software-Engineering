
from datetime import UTC, datetime
import logging

from src.domain.classes.llm.messages.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.interfaces.llm_complitions_interface import ILLMCompletions
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO


class DefaultMessageUseCase:
    def __init__(self, llm_completions: ILLMCompletions, logger: logging.Logger) -> None:
        self.llm_completions = llm_completions
        self.logger = logger

    def execute(self, user_input: DefaultInputDTO) -> DefaultOutputDTO:
        try:
            self.logger.info("Iniciando execução de DefaultMessageUseCase")

            input_message = Message(
                creation_timestamp=datetime.now(tz=UTC),
                text=user_input.message.user_input,
                source=MessageSourceEnum.USER,
            )

            llm_response = self.llm_completions.send_message(
                input_message=input_message,
                model_name=user_input.llm_model_config.provider_config.model_name,
                max_tokens=user_input.llm_model_config.max_tokens,
                temperature=user_input.llm_model_config.temperature,
            )
            if llm_response is None:
                raise ValueError("Resposta do LLM veio como None.")

            output_text = (
                llm_response.output_message.text
                if llm_response.output_message is not None
                else ""
            )

            return DefaultOutputDTO(
                message=user_input.message.user_input,
                response=output_text,
            )
        except Exception:
            self.logger.exception("Erro ao executar DefaultMessageUseCase")
            raise

