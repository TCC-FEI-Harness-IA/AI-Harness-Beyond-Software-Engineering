import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.entities.llm.llm_provider_response import LLMProviderResponse
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings

_TEXT_BLOCK_TYPE = "text"


class BaseChatCompletionsService(ILLMService, ABC):
    """Template Method comum aos provedores com API de chat completions.

    Os três provedores suportados (OpenRouter, OpenAI e Azure AI Foundry) falam o mesmo
    dialeto: o mesmo corpo de requisição e o mesmo formato de resposta. O esqueleto
    "validar → montar payload → POST → extrair texto, tokens e motivo de término" vive
    aqui uma única vez; as subclasses variam apenas o endereço, a autenticação e os
    parâmetros que cada API nomeia de um jeito.
    """

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

    # ── Pontos de variação das subclasses ────────────────────────────────────

    @property
    @abstractmethod
    def provider_label(self) -> str:
        """Nome do provedor como aparece nas mensagens de erro."""
        raise NotImplementedError

    @abstractmethod
    def missing_settings(self) -> list[str]:
        """Lista as variáveis de ambiente obrigatórias que estão sem valor.

        Returns:
            list[str]: Nomes das variáveis faltantes, vazio quando a configuração está completa.
        """
        raise NotImplementedError

    @abstractmethod
    def completions_url(self, request: LLMProviderRequest) -> str:
        """Devolve a URL de chat completions a ser chamada.

        Args:
            request: Payload técnico de envio da completion, do qual alguns provedores
                derivam parte da URL.

        Returns:
            str: URL completa da chamada.
        """
        raise NotImplementedError

    @abstractmethod
    def headers(self) -> dict[str, str]:
        """Devolve os headers da requisição, incluindo a autenticação do provedor."""
        raise NotImplementedError

    def payload_extras(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Devolve os parâmetros que só este provedor entende.

        O padrão é o `reasoning_effort` das APIs compatíveis com a OpenAI. Limitar o
        raciocínio importa porque `max_tokens` cobre raciocínio **e** resposta: sem teto,
        um modelo de raciocínio gasta o orçamento inteiro pensando e devolve conteúdo vazio.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            dict[str, Any]: Campos acrescentados ao corpo da requisição.
        """
        reasoning_effort = self.settings.llm_reasoning_effort
        if not reasoning_effort:
            return {}
        return {"reasoning_effort": reasoning_effort}

    # ── Fluxo comum ──────────────────────────────────────────────────────────

    def verify_provider_settings(self) -> bool:
        """Verifica se todas as configurações obrigatórias do provedor têm valor."""
        return not self.missing_settings()

    async def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Envia uma completion ao provedor e devolve a resposta padronizada.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            LLMProviderResponse: Resposta padronizada do provedor.

        Raises:
            ValueError: Quando configurações obrigatórias ou dados do modelo são inválidos.
            RuntimeError: Quando ocorre falha na chamada HTTP ao provedor.
            EmptyCompletionError: Quando o provedor responde sem texto utilizável.
        """
        self.validate_request(request=request)
        self.logger.info("Iniciando chamada ao provedor %s", self.provider_label)

        response_data = await self.__post_completion(request=request)

        usage = response_data.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        tokens_input = self.__extract_token_count(usage=usage, key="prompt_tokens")
        tokens_output = self.__extract_token_count(usage=usage, key="completion_tokens")
        response_id = self.__extract_response_id(response_data=response_data)

        output_text = self.__extract_output_text(response_data=response_data)
        finish_reason = self.__extract_finish_reason(response_data=response_data)
        self.__reject_empty_completion(
            output_text=output_text,
            finish_reason=finish_reason,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            response_id=response_id,
        )

        provider_response = LLMProviderResponse(
            output_text=output_text,
            input_tokens=tokens_input,
            output_tokens=tokens_output,
            finish_reason=finish_reason,
            raw_response=response_data,
            response_id=response_id,
        )

        self.logger.info("Resposta recebida com sucesso do %s", self.provider_label)
        return provider_response

    def __reject_empty_completion(
        self,
        output_text: str,
        finish_reason: str | None,
        tokens_input: int | None,
        tokens_output: int | None,
        response_id: str | None,
    ) -> None:
        """Recusa uma completion sem texto, em vez de deixá-la seguir o fluxo.

        Modelos de raciocínio devolvem `content` nulo quando o teto de tokens acaba
        durante o raciocínio interno (`finish_reason == "length"`). Sem esta recusa, o
        fluxo baseline entregaria uma resposta em branco e o fluxo harness gastaria
        todas as retentativas de parsing sobre um texto que nunca existiu. A chamada,
        porém, custou: o consumo e o identificador informados pelo provedor seguem no erro.

        Args:
            output_text: Texto extraído da resposta do provedor.
            finish_reason: Motivo de término informado pelo provedor, quando há.
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            response_id: Identificador da resposta no provedor, quando há.

        Raises:
            EmptyCompletionError: Quando o texto extraído está vazio ou em branco.
        """
        if output_text.strip():
            return

        self.logger.warning(
            "%s devolveu completion sem conteúdo. Motivo de término: '%s'",
            self.provider_label,
            finish_reason,
        )
        raise EmptyCompletionError(
            finish_reason=finish_reason,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            response_id=response_id,
        )

    def __extract_token_count(self, usage: dict[str, Any], key: str) -> int | None:
        """Extrai um contador de tokens do `usage`, distinguindo ausente de zero.

        Args:
            usage: Bloco `usage` da resposta do provedor.
            key: Nome do contador (`prompt_tokens` ou `completion_tokens`).

        Returns:
            int | None: Contador informado, ou `None` quando o provedor não o informou.
        """
        value = usage.get(key)
        if value is None:
            return None
        return int(value)

    def __extract_response_id(self, response_data: dict[str, Any]) -> str | None:
        """Extrai o identificador da resposta no provedor, quando disponível.

        Args:
            response_data: Corpo da resposta do provedor.

        Returns:
            str | None: Identificador, ou `None` quando ausente.
        """
        response_id = response_data.get("id")
        if response_id is None:
            return None
        return str(response_id)

    async def __post_completion(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Executa o POST de chat completion e devolve o corpo desserializado.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            dict[str, Any]: Corpo da resposta do provedor.

        Raises:
            RuntimeError: Quando a chamada falha ou o corpo não é um objeto JSON.
        """
        timeout_seconds = self.settings.llm_timeout_seconds

        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=timeout_seconds) as client:
                response = await client.post(
                    url=self.completions_url(request=request),
                    headers=self.headers(),
                    json=self.__build_payload(request=request),
                )
                response.raise_for_status()
                response_data = response.json()
        except httpx.HTTPStatusError as exc:
            self.logger.exception("%s retornou erro HTTP", self.provider_label)
            error_body = exc.response.text
            detail = f" Details: {error_body}" if error_body else ""
            raise RuntimeError(
                f"{self.provider_label} API returned HTTP {exc.response.status_code}.{detail}"
            ) from exc
        except httpx.RequestError as exc:
            self.logger.exception("Falha de conexão com %s", self.provider_label)
            raise RuntimeError(f"Failed to connect to {self.provider_label} API.") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError(f"{self.provider_label} API returned an invalid payload.")

        return response_data

    def validate_request(self, request: LLMProviderRequest) -> None:
        """Valida localmente a requisição de envio ao provedor, sem nenhuma chamada de rede.

        Args:
            request: Payload técnico de envio da completion.

        Raises:
            ValueError: Quando qualquer validação obrigatória falha.
        """
        missing = self.missing_settings()
        if missing:
            raise ValueError(
                f"Missing {self.provider_label} settings. "
                f"Set the {', '.join(missing)} environment variable(s)."
            )

        if request.llm_model.model_provider != self.provider:
            raise ValueError(
                f"{type(self).__name__} only supports model_provider={self.provider.name}. "
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
        """Monta o corpo de chat completions, acrescido dos extras do provedor.

        Args:
            request: Payload técnico de envio da completion.

        Returns:
            dict[str, Any]: Corpo da requisição.
        """
        payload: dict[str, Any] = {
            "model": request.llm_model.model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        payload.update(self.payload_extras(request=request))
        return payload

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
        # `content` chega como `null` quando o modelo não escreveu resposta — sem este
        # tratamento o `str(content)` do final viraria a string literal "None".
        if content is None:
            return ""

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
        if isinstance(item, dict) and item.get("type") == _TEXT_BLOCK_TYPE:
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
