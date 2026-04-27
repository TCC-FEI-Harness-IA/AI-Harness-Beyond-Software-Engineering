import json

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.settings_interface import ISettings


class GenaiModel:
    """Representa os dados de identificação e validação de um modelo GenAI.

    Attributes:
        model_name: Nome do modelo.
        model_provider: Provedor do modelo.
    """

    def __init__(
        self,
        settings: ISettings,
        model_name: str | None = None,
        model_provider: ModelProviderEnum | None = None,
    ) -> None:
        """Inicializa uma instância de informações de LLM.

        Args:
            model_name: Nome do modelo.
            model_provider: Provedor do modelo.
        """
        self.model_name = model_name
        self.model_provider = model_provider
        self.available_models: set[str] | None = None
        self.available_providers: set[str] | None = None
        self.settings = settings

    def new(self, model_name: str, model_provider: ModelProviderEnum) -> None:
        """Inicializa o modelo GenAI inferindo valores internos de validação.

        As validações de modelo e provedor são executadas automaticamente.

        Args:
            model_name: Nome do modelo.
            model_provider: Provedor do modelo.

        Raises:
            ValueError: Quando a instância já possui dados.
            ValueError: Quando o modelo informado não está disponível.
            ValueError: Quando o provedor informado não está disponível.
        """
        if any(
            value is not None
            for value in (
                self.model_name,
                self.model_provider,
                self.available_models,
                self.available_providers,
            )
        ):
            raise ValueError("Cannot call `new` on a GenaiModel that already has data.")

        self.model_name = model_name
        self.model_provider = model_provider
        self.available_models = self.__load_available_models()
        self.available_providers = self.__load_available_providers()

        if not self.verify_model():
            raise ValueError(f"Model '{self.model_name}' is not available.")

        if not self.verify_provider():
            raise ValueError(f"Provider '{self.model_provider.value}' is not available.")

    def verify_model(self) -> bool:
        """Verifica se o modelo atual está na lista de modelos disponíveis.

        Returns:
            bool: `True` quando o modelo atual é válido.
        """
        if self.model_name is None or self.available_models is None:
            return False

        return self.model_name.lower() in self.available_models

    def verify_provider(self) -> bool:
        """Verifica se o provedor atual está na lista de provedores disponíveis.

        Returns:
            bool: `True` quando o provedor atual é válido.
        """
        if self.model_provider is None or self.available_providers is None:
            return False

        return self.model_provider.value.lower() in self.available_providers

    def __load_available_models(self) -> set[str]:
        """Carrega os modelos disponíveis da variável `genai_avaliable_models`.

        Returns:
            set[str]: Conjunto normalizado (lowercase) de modelos permitidos.
        """
        raw_value = (self.settings.get_var_env("genai_avaliable_models") or "").strip()
        if not raw_value:
            return set()

        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return {str(item).strip().lower() for item in parsed if str(item).strip()}
        except json.JSONDecodeError:
            pass

        return {item.strip().lower() for item in raw_value.split(",") if item.strip()}

    def __load_available_providers(self) -> set[str]:
        """Carrega os provedores disponíveis da variável `genai_avaliable_providers`.

        Aceita dois formatos:
        - JSON list, por exemplo: `["open_router", "chatgpt"]`
        - CSV simples, por exemplo: `open_router,chatgpt`

        Returns:
            set[str]: Conjunto normalizado (lowercase) de provedores permitidos.
        """
        raw_value = (self.settings.get_var_env("genai_avaliable_providers") or "").strip()
        if not raw_value:
            return set()

        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return {str(item).strip().lower() for item in parsed if str(item).strip()}
        except json.JSONDecodeError:
            pass

        return {item.strip().lower() for item in raw_value.split(",") if item.strip()}
