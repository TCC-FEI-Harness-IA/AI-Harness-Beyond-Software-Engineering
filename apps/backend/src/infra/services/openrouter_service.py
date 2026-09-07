import logging
from typing import Any

import httpx

from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.entities.llm.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class OpenRouterService(ILLMService):
    """Serviço assíncrono de integração com a API de chat completions da OpenRouter."""

    def __init__(
        self,
        logger: logging.Logger,
        settings: ISettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Inicializa o serviço.

        Args:
            logger: Logger do módulo.
            settings: Configurações da aplicação.
            transport: Transporte HTTP alternativo. Existe para permitir a substituição
                da camada de rede em teste; em produção fica `None` e o `httpx` usa o
                transporte padrão.
        """
        self.logger = logger
        self.settings: ISettings = settings
        self.transport: httpx.AsyncBaseTransport | None = transport

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.OPEN_ROUTER

    def verify_provider_settings(self) -> bool:
        """Verifica se a API key necessária para OpenRouter está disponível."""
        return bool(self.settings.openrouter_api_key)

    async def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Envia uma completion para a OpenRouter e retorna a resposta padronizada.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            LLMProviderResponse: Resposta padronizada do provedor.

        Raises:
            ValueError: Quando configurações obrigatórias ou dados do modelo são inválidos.
            RuntimeError: Quando ocorre falha na chamada HTTP para a OpenRouter.
        """
        self.logger.info("Iniciando chamada ao provedor OpenRouter")
        self.__run_message_validations(request=request)

        response_data = await self.__post_completion(request=request)

        usage = response_data.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}

        provider_response = LLMProviderResponse(
            output_text=self.__extract_output_text(response_data=response_data),
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            finish_reason=self.__extract_finish_reason(response_data=response_data),
            raw_response=response_data,
        )

        self.logger.info("Resposta recebida com sucesso do OpenRouter")
        return provider_response

    async def __post_completion(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Executa o POST de chat completion e devolve o corpo desserializado.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            dict[str, Any]: Corpo da resposta do provedor.

        Raises:
            RuntimeError: Quando a chamada falha ou o corpo não é um objeto JSON.
        """
        timeout_seconds = self.settings.openrouter_timeout_seconds

        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=timeout_seconds) as client:
                response = await client.post(
                    url=self.settings.openrouter_api_url,
                    headers=self.__build_headers(),
                    json=self.__build_payload(request=request),
                )
                response.raise_for_status()
                response_data = response.json()
        except httpx.HTTPStatusError as exc:
            self.logger.exception("OpenRouter retornou erro HTTP")
            error_body = exc.response.text
            detail = f" Details: {error_body}" if error_body else ""
            raise RuntimeError(f"OpenRouter API returned HTTP {exc.response.status_code}.{detail}") from exc
        except httpx.RequestError as exc:
            self.logger.exception("Falha de conexão com OpenRouter")
            raise RuntimeError("Failed to connect to OpenRouter API.") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("OpenRouter API returned an invalid payload.")

        return response_data

    def __run_message_validations(self, request: LLMProviderRequest) -> None:
        """Executa as validações de entrada para envio de mensagem ao provedor.

        Args:
            request: Payload técnico de envio da completion.

        Raises:
            ValueError: Quando qualquer validação obrigatória falha.
        """
        if not self.verify_provider_settings():
            raise ValueError("Missing OpenRouter settings. Set OPENROUTER_API_KEY environment variable.")

        if request.llm_model.model_provider != self.provider:
            raise ValueError(
                "OpenRouterService only supports model_provider=OPEN_ROUTER. "
                f"Received: {request.llm_model.model_provider}."
            )

        if not request.llm_model.model_name.strip():
            raise ValueError("GenaiModel.model_name must be defined.")

        if request.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")

        if not request.messages:
            raise ValueError("request.messages must contain at least one message.")

        for message in request.messages:
            if not message.role.strip():
                raise ValueError("message.role must not be empty.")

            if not message.content.strip():
                raise ValueError("message.content must not be empty.")

    def __build_payload(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Monta o payload compatível com a API da OpenRouter.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            dict[str, Any]: Corpo da requisição.
        """
        return {
            "model": request.llm_model.model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

    def __build_headers(self) -> dict[str, str]:
        """Monta os headers padrão da requisição à OpenRouter.

        Returns:
            dict[str, str]: Headers da requisição.
        """
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        http_referer = self.settings.openrouter_http_referer
        if http_referer:
            headers["HTTP-Referer"] = http_referer

        title = self.settings.openrouter_x_title
        if title:
            headers["X-Title"] = title

        return headers

    def __extract_output_text(self, response_data: dict[str, Any]) -> str:
        """Extrai o texto principal da resposta do provedor.

        Args:
            response_data: Corpo da resposta do provedor.

        Returns:
            str: Texto gerado, ou vazio quando a resposta não o contém.
        """
        message = self.__extract_message(response_data=response_data)
        if message is None:
            return ""

        content = message.get("content", "")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "".join(self.__extract_text_block(item=item) for item in content)

        return str(content)

    def __extract_text_block(self, item: Any) -> str:
        """Extrai o texto de um bloco de conteúdo estruturado.

        Args:
            item: Bloco de conteúdo devolvido pelo provedor.

        Returns:
            str: Texto do bloco, ou vazio quando o bloco não carrega texto.
        """
        if isinstance(item, dict) and item.get("type") == "text":
            return str(item.get("text", ""))

        if isinstance(item, str):
            return item

        return ""

    def __extract_finish_reason(self, response_data: dict[str, Any]) -> str | None:
        """Extrai o motivo de término da geração, quando disponível.

        Args:
            response_data: Corpo da resposta do provedor.

        Returns:
            str | None: Motivo de término, ou `None` quando ausente.
        """
        first_choice = self.__extract_first_choice(response_data=response_data)
        if first_choice is None:
            return None

        finish_reason = first_choice.get("finish_reason")
        if finish_reason is None:
            return None

        return str(finish_reason)

    def __extract_first_choice(self, response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Devolve a primeira escolha da resposta, quando ela é utilizável.

        Args:
            response_data: Corpo da resposta do provedor.

        Returns:
            dict[str, Any] | None: Primeira escolha, ou `None` quando ausente ou malformada.
        """
        choices = response_data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        return first_choice

    def __extract_message(self, response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Devolve a mensagem da primeira escolha, quando ela é utilizável.

        Args:
            response_data: Corpo da resposta do provedor.

        Returns:
            dict[str, Any] | None: Mensagem, ou `None` quando ausente ou malformada.
        """
        first_choice = self.__extract_first_choice(response_data=response_data)
        if first_choice is None:
            return None

        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            return None

        return message
