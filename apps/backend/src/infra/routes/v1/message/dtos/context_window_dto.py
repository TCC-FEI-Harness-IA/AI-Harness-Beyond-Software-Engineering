from pydantic import BaseModel


class ContextWindowDTO(BaseModel):
    """Identidade e tamanho da janela de contexto no momento do evento."""

    context_id: str
    context_size: int
