from pydantic import BaseModel, ConfigDict

from src.infra.routes.v1.message.dtos.message_input_dto import MessageInputDTO
from src.infra.routes.v1.message.dtos.model_config_dto import ModelConfigDTO


class DefaultInputDTO(BaseModel):
    """Corpo da requisição do fluxo baseline."""

    model_config = ConfigDict(protected_namespaces=())

    message: MessageInputDTO
    llm_model_config: ModelConfigDTO
