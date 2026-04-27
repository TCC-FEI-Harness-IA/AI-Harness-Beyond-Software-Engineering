import json
import logging

import requests

from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.llm_service_provider.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class OpenRouterService(ILLMService):
    """Serviço simples de integração com a API de chat completions da OpenRouter."""

    def __init__(self, logger: logging.Logger, settings: ISettings) -> None:
        self.logger = logger
        self.settings = settings

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.OPEN_ROUTER

    def __get_endpoint(self) -> str:
        """Obtém o endpoint da OpenRouter a partir de variável de ambiente."""
        return self.settings.get_var_env("OPENROUTER_API_URL")

    def __get_api_key(self) -> str:
        """Obtém a API key da OpenRouter a partir de variável de ambiente."""
        return self.settings.get_var_env("OPENROUTER_API_KEY").strip()

    def __run_message_validations(
        self,
        request: LLMProviderRequest,
    ) -> None:
        """Executa validações de entrada para envio de mensagem ao provedor.

        Raises:
            ValueError: Quando qualquer validação obrigatória falha.
        """
        if not self.verify_provider_settings():
            raise ValueError("Missing OpenRouter settings. Set OPENROUTER_API_KEY environment variable.")

        if request.llm_model.model_provider != self.provider:
            raise ValueError("OpenRouterService only supports model_provider=OPEN_ROUTER.")

        if request.llm_model.model_name is None or not request.llm_model.model_name.strip():
            raise ValueError("GenaiModel.model_name must be defined.")

        if request.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")

        if request.temperature is not None and request.temperature < 0:
            raise ValueError("temperature must be greater than or equal to zero.")

        if not request.messages:
            raise ValueError("request.messages must contain at least one message.")

        for message in request.messages:
            if message.role.strip() == "":
                raise ValueError("message.role must not be empty.")

            if message.content.strip() == "":
                raise ValueError("message.content must not be empty.")

    def __build_payload(self, request: LLMProviderRequest) -> dict[str, object]:
        """Monta payload compatível com API da OpenRouter."""
        payload: dict[str, object] = {
            "model": request.llm_model.model_name,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "max_tokens": request.max_tokens,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature

        return payload

    def __extract_output_text(self, response_data: dict[str, object]) -> str:
        """Extrai o texto principal da resposta do provedor."""
        choices = response_data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""

        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            return ""

        content = message.get("content", "")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "".join(text_parts)

        return str(content)

    def __extract_finish_reason(self, response_data: dict[str, object]) -> str | None:
        """Extrai o motivo de término da geração, quando disponível."""
        choices = response_data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        finish_reason = first_choice.get("finish_reason")
        if finish_reason is None:
            return None

        return str(finish_reason)

    def __build_headers(self) -> dict[str, str]:
        """Monta os headers padrões para requisição OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.__get_api_key()}",
            "Content-Type": "application/json",
        }

        http_referer = (self.settings.get_var_env("OPENROUTER_HTTP_REFERER") or "").strip()
        if http_referer:
            headers["HTTP-Referer"] = http_referer

        title = (self.settings.get_var_env("OPENROUTER_X_TITLE") or "").strip()
        if title:
            headers["X-OpenRouter-Title"] = title

        return headers

    def verify_provider_settings(self) -> bool:
        """Verifica se a API key necessária para OpenRouter está disponível."""
        return bool(self.__get_api_key())

    def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Envia uma completion para OpenRouter e retorna resposta padronizada.

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

        endpoint = self.__get_endpoint()
        payload = self.__build_payload(request=request)
        headers = self.__build_headers()

        try:
            timeout_seconds = float(self.settings.get_var_env("OPENROUTER_TIMEOUT_SECONDS") or "30")
            response = requests.post(
                url=endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.HTTPError as exc:
            self.logger.exception("OpenRouter retornou erro HTTP")
            error_body = ""
            if exc.response is not None:
                error_body = exc.response.text
            detail = f" Details: {error_body}" if error_body else ""
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"OpenRouter API returned HTTP {status_code}.{detail}") from exc
        except requests.RequestException as exc:
            self.logger.exception("Falha de conexão com OpenRouter")
            raise RuntimeError("Failed to connect to OpenRouter API.") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("OpenRouter API returned an invalid payload.")

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
