from pydantic import BaseModel


class DefaultOutputDTO(BaseModel):
    """Corpo da resposta do fluxo baseline."""

    message: str
    response: str
    session_id: str
    tokens_input: int
    tokens_output: int
    inference_time_ms: int
