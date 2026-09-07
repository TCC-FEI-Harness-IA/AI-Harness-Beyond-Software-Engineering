from pydantic import BaseModel


class DefaultOutputDTO(BaseModel):
    """Corpo da resposta do fluxo baseline."""

    message: str
    response: str
