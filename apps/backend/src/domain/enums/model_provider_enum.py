from enum import StrEnum


class ModelProviderEnum(StrEnum):
    """Enum dos provedores suportados para modelos de LLM."""

    OPEN_ROUTER = "open_router"
    AZURE_FOUNDRY = "azure_foundry"
    MOCK = "mock"
