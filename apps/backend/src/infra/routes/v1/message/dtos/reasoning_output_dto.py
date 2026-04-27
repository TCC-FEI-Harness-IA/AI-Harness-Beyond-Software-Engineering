from pydantic import BaseModel


class ReasoningOutputDTO(BaseModel):
    message: str
    reasoning: str
