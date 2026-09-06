import json
import logging
from typing import Any

import requests

from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.llm_service_provider.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class AzureFoundryService(ILLMService):
    """Serviço de integração com a API de Chat Completions do Azure AI Foundry.

    Suporta endpoints Serverless / Models-as-a-Service (MaaS) para modelos da
    família Llama 3.1 (8B, 70B, 405B) e endpoints de inferência do Azure AI Studio.
    """

    def __init__(self, logger: logging.Logger, settings: ISettings) -> None:
        self.logger = logger
        self.settings = settings

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor atendido pelo serviço."""
        return ModelProviderEnum.AZURE_FOUNDRY

    def __get_default_endpoint(self) -> str:
        """Obtém o endpoint padrão da Azure AI Foundry das variáveis de ambiente."""
        try:
            return (self.settings.get_var_env("AZURE_FOUNDRY_ENDPOINT") or "").strip()
        except ValueError:
            return ""

    def __get_api_key(self) -> str:
        """Obtém a chave de API da Azure AI Foundry das variáveis de ambiente."""
        try:
            return (self.settings.get_var_env("AZURE_FOUNDRY_API_KEY") or "").strip()
        except ValueError:
            return ""

    def verify_provider_settings(self) -> bool:
        """Verifica se as configurações mínimas do provedor estão disponíveis."""
        return bool(self.__get_api_key()) and bool(self.__get_default_endpoint())

    def __validate_request(self, request: LLMProviderRequest, endpoint: str) -> None:
        """Valida se o request possui dados consistentes para envio à API."""
        if not endpoint:
            raise ValueError(
                "Endpoint da Azure AI Foundry não configurado. "
                "Defina AZURE_FOUNDRY_ENDPOINT no .env ou informe no payload."
            )

        api_key = self.__get_api_key()
        if not api_key:
            raise ValueError(
                "API Key da Azure AI Foundry não configurada. "
                "Defina AZURE_FOUNDRY_API_KEY no arquivo .env."
            )

        if not request.messages:
            raise ValueError("A requisição deve conter pelo menos uma mensagem.")

        for msg in request.messages:
            if not msg.role or not msg.role.strip():
                raise ValueError("O campo 'role' da mensagem não pode ser vazio.")
            if not msg.content or not msg.content.strip():
                raise ValueError("O campo 'content' da mensagem não pode ser vazio.")

    def __build_headers(self) -> dict[str, str]:
        """Monta headers de autenticação para endpoints Azure MaaS e Inference."""
        api_key = self.__get_api_key()
        return {
            "Content-Type": "application/json",
            "api-key": api_key,
            "Authorization": f"Bearer {api_key}",
        }

    def __build_payload(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Monta o payload de requisição no padrão OpenAI / Azure AI Inference."""
        payload: dict[str, Any] = {
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        if request.llm_model.model_name:
            payload["model"] = request.llm_model.model_name

        return payload

    def __extract_output_text(self, response_data: dict[str, Any]) -> str:
        """Extrai o texto retornado pela API."""
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
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)

        return str(content)

    def __extract_finish_reason(self, response_data: dict[str, Any]) -> str | None:
        """Extrai o motivo de finalização da geração."""
        choices = response_data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        reason = first_choice.get("finish_reason")
        return str(reason) if reason is not None else None

    def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Executa a chamada HTTP à Azure AI Foundry e retorna resposta padronizada."""
        custom_endpoint = request.metadata.get("endpoint") if request.metadata else None
        endpoint = str(custom_endpoint).strip() if custom_endpoint else self.__get_default_endpoint()

        self.__validate_request(request=request, endpoint=endpoint)
        self.logger.info("Enviando requisição para Azure AI Foundry no endpoint: %s", endpoint)

        payload = self.__build_payload(request=request)
        headers = self.__build_headers()

        try:
            timeout_str = self.settings.get_var_env("AZURE_FOUNDRY_TIMEOUT_SECONDS") or "60"
            timeout = float(timeout_str)
        except (ValueError, TypeError):
            timeout = 60.0

        try:
            response = requests.post(
                url=endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.HTTPError as exc:
            self.logger.exception("Azure AI Foundry retornou erro HTTP")
            error_body = exc.response.text if exc.response is not None else ""
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"Azure AI Foundry retornou HTTP {status_code}: {error_body}") from exc
        except requests.RequestException as exc:
            self.logger.exception("Falha na conexão com Azure AI Foundry")
            raise RuntimeError(f"Falha de rede ao contatar Azure AI Foundry: {exc}") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("Azure AI Foundry retornou payload JSON inválido.")

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

        self.logger.info("Resposta recebida com sucesso da Azure AI Foundry")
        return provider_response
