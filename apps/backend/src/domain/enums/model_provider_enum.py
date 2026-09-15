from enum import StrEnum


class ModelProviderEnum(StrEnum):
    """Enum dos provedores suportados para modelos de LLM.

    Os três expõem a mesma API de chat completions; o que muda entre eles é a URL,
    a forma de autenticação e o vocabulário de alguns parâmetros — diferenças que
    ficam contidas na implementação de `ILLMService` de cada um.
    """

    OPEN_ROUTER = "open_router"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"
    OPENAI = "openai"
