from src.domain.entities.llm.model_info import ModelInfo
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class InMemoryModelInfoRepository(IModelInfoRepository):
    """Dublê de `IModelInfoRepository` apoiado em dicionário, opcionalmente programado para falhar."""

    def __init__(self, models: list[ModelInfo] | None = None, error: Exception | None = None) -> None:
        """Prepara o armazenamento em memória.

        Args:
            models: Modelos já cadastrados.
            error: Exceção levantada por toda consulta, quando informada.
        """
        self.models: dict[str, ModelInfo] = {model.model_name: model for model in models or []}
        self.error = error
        self.find_calls: list[str] = []

    async def list_all(self) -> list[ModelInfo]:
        self.__raise_if_programmed()
        return [self.models[name] for name in sorted(self.models)]

    async def find_by_name(self, model_name: str) -> ModelInfo | None:
        self.find_calls.append(model_name)
        self.__raise_if_programmed()
        return self.models.get(model_name)

    async def save(self, model: ModelInfo) -> None:
        self.__raise_if_programmed()
        self.models[model.model_name] = model

    async def delete(self, model_name: str) -> bool:
        self.__raise_if_programmed()
        return self.models.pop(model_name, None) is not None

    def __raise_if_programmed(self) -> None:
        if self.error is not None:
            raise self.error
