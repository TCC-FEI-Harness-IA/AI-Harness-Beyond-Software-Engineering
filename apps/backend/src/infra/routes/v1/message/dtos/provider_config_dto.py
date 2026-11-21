from pydantic import BaseModel, ConfigDict


class ProviderConfigDTO(BaseModel):
    """Configuração específica do provedor escolhido pelo cliente."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    endpoint: str | None = None
