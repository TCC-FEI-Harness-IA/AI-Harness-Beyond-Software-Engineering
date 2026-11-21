from src.domain.entities.llm.model_info import ModelInfo
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class LayeredModelInfoRepository(IModelInfoRepository):
    """Catálogo visto por uma conta: o pessoal sobre o compartilhado.

    Leituras consultam primeiro o catálogo pessoal e depois o compartilhado; escritas e remoções
    afetam só o pessoal, então o catálogo compartilhado é somente leitura para usuários comuns.
    """

    def __init__(self, personal: IModelInfoRepository, shared: IModelInfoRepository) -> None:
        """Inicializa o catálogo em camadas.

        Args:
            personal: Catálogo pessoal da conta.
            shared: Catálogo compartilhado (somente leitura aqui).
        """
        self.personal = personal
        self.shared = shared

    async def list_all(self) -> list[ModelInfo]:
        """Modelos dos dois níveis; o pessoal prevalece sobre o compartilhado de mesmo nome."""
        merged = {model.model_name: model for model in await self.shared.list_all()}
        merged.update({model.model_name: model for model in await self.personal.list_all()})
        return [merged[name] for name in sorted(merged)]

    async def find_by_name(self, model_name: str) -> ModelInfo | None:
        """Busca no pessoal e, se não houver, no compartilhado."""
        return await self.personal.find_by_name(model_name) or await self.shared.find_by_name(model_name)

    async def save(self, model: ModelInfo) -> None:
        """Grava no catálogo pessoal."""
        await self.personal.save(model=model)

    async def delete(self, model_name: str) -> bool:
        """Remove do catálogo pessoal; um modelo só compartilhado não é removido."""
        return await self.personal.delete(model_name=model_name)

    async def is_shared(self, model_name: str) -> bool:
        """Informa se o modelo visível para a conta vem do catálogo compartilhado."""
        return await self.personal.find_by_name(model_name) is None and (
            await self.shared.find_by_name(model_name) is not None
        )
