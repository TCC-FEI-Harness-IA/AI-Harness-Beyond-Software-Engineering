from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.model_catalog_interface import IModelCatalog


class FakeModelCatalog(IModelCatalog):
    """Dublê de `IModelCatalog` que libera tudo, salvo quando programado para recusar."""

    def __init__(self, error: Exception | None = None, context_length: int | None = None) -> None:
        """Configura o dublê.

        Args:
            error: Exceção levantada por `resolve`, quando informada.
            context_length: Contexto máximo informado em todo modelo resolvido.
        """
        self.error = error
        self.context_length = context_length
        self.resolved: list[tuple[str, ModelProviderEnum]] = []

    def resolve(self, model_name: str, model_provider: ModelProviderEnum) -> GenaiModel:
        """Captura a consulta e devolve o modelo pedido."""
        self.resolved.append((model_name, model_provider))

        if self.error is not None:
            raise self.error

        return GenaiModel(model_name=model_name, model_provider=model_provider, context_length=self.context_length)

    def is_model_available(self, model_name: str) -> bool:
        """Todo modelo está disponível no dublê."""
        return True

    def is_provider_available(self, model_provider: ModelProviderEnum) -> bool:
        """Todo provedor está disponível no dublê."""
        return True
