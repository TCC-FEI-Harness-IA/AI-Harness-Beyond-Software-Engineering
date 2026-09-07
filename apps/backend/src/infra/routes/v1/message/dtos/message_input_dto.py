from pydantic import BaseModel


class MessageInputDTO(BaseModel):
    """Mensagem enviada pelo cliente no corpo da requisição."""

    user_input: str
