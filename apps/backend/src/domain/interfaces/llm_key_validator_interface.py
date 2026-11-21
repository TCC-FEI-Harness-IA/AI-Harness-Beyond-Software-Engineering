from abc import ABC, abstractmethod


class ILLMKeyValidator(ABC):
    """Confirma com o provedor que uma chave de API é aceita, sem consumir créditos."""

    @abstractmethod
    async def validate(self, api_key: str) -> None:
        """Valida a chave.

        Raises:
            CredentialRejectedError: Quando o provedor recusa a chave.
            LLMKeyValidationUnavailableError: Quando a validação não pôde ser feita agora.
        """
        raise NotImplementedError
