from pydantic import BaseModel


class ChatInputDTO(BaseModel):
    message: str
