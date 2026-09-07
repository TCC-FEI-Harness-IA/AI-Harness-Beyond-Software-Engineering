from dataclasses import dataclass

from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class GenaiModel:
    """Identifica um modelo de GenAI já validado contra o catálogo.

    A validação contra as allowlists é responsabilidade de `IModelCatalog`; esta
    entidade carrega apenas os dados do modelo, sem depender de configuração.

    Attributes:
        model_name: Nome do modelo.
        model_provider: Provedor do modelo.
    """

    model_name: str
    model_provider: ModelProviderEnum
