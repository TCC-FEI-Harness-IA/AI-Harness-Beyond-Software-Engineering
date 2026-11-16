from inspect import getfile

from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.services.openrouter_service import OpenRouterService


class LLMServiceFactory:
    """Instancia os serviços de LLM disponíveis na aplicação hospedada.

    Na versão multiusuário só a OpenRouter é oferecida, sempre com a chave do próprio usuário (na
    autorização da execução). Os adapters da OpenAI e do Azure AI Foundry continuam no código, mas
    não são registrados: as credenciais desses provedores configuradas no servidor nunca são
    consumidas por requisições de usuários.
    """

    def __init__(self, settings: ISettings) -> None:
        """Inicializa a fábrica.

        Args:
            settings: Configurações da aplicação, injetadas em cada serviço criado.
        """
        self.settings: ISettings = settings

    def create_all(self, authorization: ExecutionAuthorization | None) -> list[ILLMService]:
        """Cria os serviços de uma requisição ou execução.

        Args:
            authorization: Autorização com a credencial do usuário; `None` deixa a OpenRouter sem
                credencial (toda chamada é recusada localmente).

        Returns:
            list[ILLMService]: A OpenRouter, ligada à credencial informada.
        """
        return [
            OpenRouterService(
                logger=self.settings.logger(module_file=getfile(OpenRouterService)),
                settings=self.settings,
                authorization=authorization,
            )
        ]
