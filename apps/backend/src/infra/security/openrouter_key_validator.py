import logging
import re

import httpx

from src.domain.errors.credential_rejected_error import CredentialRejectedError
from src.domain.errors.llm_key_validation_unavailable_error import LLMKeyValidationUnavailableError
from src.domain.interfaces.llm_key_validator_interface import ILLMKeyValidator

# Formato tolerante (sem espaços nem controle, tamanho razoável); a decisão final é da OpenRouter.
_KEY_PATTERN = re.compile(r"^[\x21-\x7e]{8,256}$")
_REJECTED_STATUSES = (401, 403)


class OpenRouterKeyValidator(ILLMKeyValidator):
    """Valida a chave com `GET /api/v1/key` da OpenRouter, que não consome créditos.

    A chave nunca entra em logs nem em mensagens de erro.
    """

    def __init__(
        self,
        validation_url: str,
        logger: logging.Logger,
        timeout_seconds: float = 10,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Inicializa o validador.

        Args:
            validation_url: Endpoint de consulta da chave.
            logger: Logger do módulo.
            timeout_seconds: Tempo máximo da consulta.
            transport: Transporte HTTP alternativo, para testes.
        """
        self.validation_url = validation_url
        self.logger = logger
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def validate(self, api_key: str) -> None:
        """Valida a chave junto à OpenRouter.

        Raises:
            CredentialRejectedError: Formato impossível ou recusa da OpenRouter (401/403).
            LLMKeyValidationUnavailableError: Falha de rede ou resposta inesperada.
        """
        if not _KEY_PATTERN.fullmatch(api_key):
            raise CredentialRejectedError()
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=self.timeout_seconds) as client:
                response = await client.get(self.validation_url, headers={"Authorization": f"Bearer {api_key}"})
        except httpx.HTTPError as exc:
            self.logger.warning("Validação da chave OpenRouter indisponível: %s", type(exc).__name__)
            raise LLMKeyValidationUnavailableError() from None
        if response.status_code in _REJECTED_STATUSES:
            self.logger.info("A OpenRouter recusou uma chave (HTTP %s)", response.status_code)
            raise CredentialRejectedError()
        if response.status_code != 200:
            self.logger.warning("Validação da chave OpenRouter respondeu HTTP %s", response.status_code)
            raise LLMKeyValidationUnavailableError()
