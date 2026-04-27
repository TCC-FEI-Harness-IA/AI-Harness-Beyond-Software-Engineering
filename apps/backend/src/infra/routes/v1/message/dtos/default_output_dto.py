from pydantic import BaseModel


class DefaultOutputDTO(BaseModel):
    message: str
    response: str
