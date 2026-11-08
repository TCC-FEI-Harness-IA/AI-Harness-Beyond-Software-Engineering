from pydantic import BaseModel, Field


class MessageInputDTO(BaseModel):
    """Mensagem enviada pelo cliente no corpo da requisição."""

    user_input: str = Field(min_length=1)
