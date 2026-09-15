from inspect import getfile

from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings
from src.infra.services.azure_ai_foundry_service import AzureAIFoundryService
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService
from src.infra.services.openai_service import OpenAIService
from src.infra.services.openrouter_service import OpenRouterService

_SERVICE_CLASSES: tuple[type[BaseChatCompletionsService], ...] = (
    OpenRouterService,
    AzureAIFoundryService,
    OpenAIService,
)


class LLMServiceFactory:
    """Instancia as implementações de `ILLMService` de todos os provedores suportados.

    Os dois composition roots (baseline e harness) precisam exatamente do mesmo conjunto
    de serviços; concentrá-lo aqui evita que um deles fique para trás quando um provedor
    novo entra. Instanciar todos é barato: nenhum serviço abre conexão na construção, e a
    validação de credenciais só acontece na primeira chamada ao provedor escolhido.
    """

    def __init__(self, settings: ISettings) -> None:
        """Inicializa a fábrica.

        Args:
            settings: Configurações da aplicação, injetadas em cada serviço criado.
        """
        self.settings: ISettings = settings

    def create_all(self) -> list[ILLMService]:
        """Cria uma instância de cada provedor suportado.

        Returns:
            list[ILLMService]: Um serviço por membro de `ModelProviderEnum`.
        """
        return [
            service_class(
                logger=self.settings.logger(module_file=getfile(service_class)),
                settings=self.settings,
            )
            for service_class in _SERVICE_CLASSES
        ]
