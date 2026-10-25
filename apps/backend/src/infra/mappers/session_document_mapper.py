from datetime import datetime
from dataclasses import asdict
from enum import StrEnum
from typing import Any, TypeVar

from src.domain.entities.llm.message import Message
from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session import Session
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper

_DOCUMENT_ID_KEY = "_id"
_SESSION_CONTAINER = "sessão"
_TOTALS_CONTAINER = "totais da sessão"
_MESSAGE_CONTAINER = "mensagem da sessão"
_DEGRADATION_CONTAINER = "degradação da sessão"
_INVOCATION_CONTAINER = "invocação da sessão"
_FAILURE_CONTAINER = "falha da sessão"
_PROMPT_INPUT_CONTAINER = "prompt de entrada da mensagem"

TEnum = TypeVar("TEnum", bound=StrEnum)


class SessionDocumentMapper(ISessionDocumentMapper):
    """Data Mapper entre `Session` e o documento persistido (`dict`).

    O documento produzido é JSON puro: datas viram strings ISO-8601 com offset e
    enums viram os respectivos `value`. É o mesmo documento que um repositório de
    MongoDB gravaria, por isso a chave primária é `_id`, espelhada em `id`.

    Documentos gravados antes do registro por invocação, da falha estruturada, do provedor e do
    prompt de entrada das mensagens continuam legíveis: as chaves novas são opcionais na leitura,
    a ausência de `prompt_input` vira uma conversa vazia e a ausência de `invocations` marca os
    totais como legados em vez de inventar chamadas passadas.
    """

    def to_document(self, session: Session) -> dict[str, Any]:
        """Converte uma sessão no documento a ser persistido.

        Args:
            session: Sessão a ser convertida.

        Returns:
            dict[str, Any]: Documento equivalente à sessão, serializável em JSON.
        """
        return {
            _DOCUMENT_ID_KEY: session.id,
            "id": session.id,
            "benchmark_details": asdict(session.benchmark_details),
            "user_question": session.user_question,
            "flow": session.flow.value,
            "model_name": session.model_name,
            "max_tokens": session.max_tokens,
            "temperature": session.temperature,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "final_answer": session.final_answer,
            "provider": session.provider.value if session.provider is not None else None,
            "failure": self.__failure_to_document(failure=session.failure),
            "legacy_totals": session.legacy_totals,
            "totals": self.__totals_to_document(totals=session.totals),
            "messages": [self.__message_to_document(message=message) for message in session.messages],
            "degradations": [
                self.__degradation_to_document(degradation=degradation) for degradation in session.degradations
            ],
            "invocations": [
                self.__invocation_to_document(invocation=invocation) for invocation in session.invocations
            ],
        }

    @staticmethod
    def __benchmark_from_document(document: dict[str, Any]) -> BenchmarkDetails:
        """Sessões antigas recebem o valor padrão não benchmark."""
        raw = document.get("benchmark_details")
        if raw is None:
            return BenchmarkDetails()
        if not isinstance(raw, dict):
            raise ValueError("benchmark_details deve ser um objeto.")
        values = dict(raw)
        if values.get("inference_mode") is not None:
            values["inference_mode"] = BenchmarkInferenceModeEnum(values["inference_mode"])
        try:
            return BenchmarkDetails(**values)
        except TypeError as error:
            raise ValueError("Campos inválidos em benchmark_details.") from error

    def from_document(self, document: dict[str, Any]) -> Session:
        """Converte um documento persistido de volta em uma sessão.

        Args:
            document: Documento persistido.

        Returns:
            Session: Sessão equivalente ao documento.

        Raises:
            ValueError: Quando falta uma chave obrigatória, um enum tem valor
                desconhecido ou uma data não é ISO-8601 com fuso horário.
        """
        session = Session(
            benchmark_details=self.__benchmark_from_document(document),
            id=self.__required(document=document, key=_DOCUMENT_ID_KEY, container=_SESSION_CONTAINER),
            user_question=self.__required(document=document, key="user_question", container=_SESSION_CONTAINER),
            flow=self.__enum_from_document(
                document=document, key="flow", container=_SESSION_CONTAINER, enum_type=ThinkingPhaseEnum
            ),
            model_name=self.__required(document=document, key="model_name", container=_SESSION_CONTAINER),
            max_tokens=self.__required(document=document, key="max_tokens", container=_SESSION_CONTAINER),
            temperature=self.__required(document=document, key="temperature", container=_SESSION_CONTAINER),
            status=self.__enum_from_document(
                document=document, key="status", container=_SESSION_CONTAINER, enum_type=SessionStatusEnum
            ),
            created_at=self.__datetime_from_document(
                document=document, key="created_at", container=_SESSION_CONTAINER
            ),
            updated_at=self.__datetime_from_document(
                document=document, key="updated_at", container=_SESSION_CONTAINER
            ),
            final_answer=self.__required(document=document, key="final_answer", container=_SESSION_CONTAINER),
            provider=self.__optional_provider(document=document),
            failure=self.__failure_from_optional_document(document=document.get("failure")),
        )
        session.totals = self.__totals_from_document(
            document=self.__required(document=document, key="totals", container=_SESSION_CONTAINER)
        )
        session.messages = [
            self.__message_from_document(document=item)
            for item in self.__required(document=document, key="messages", container=_SESSION_CONTAINER)
        ]
        session.degradations = [
            self.__degradation_from_document(document=item)
            for item in self.__required(document=document, key="degradations", container=_SESSION_CONTAINER)
        ]
        session.invocations = [
            self.__invocation_from_document(document=item) for item in document.get("invocations", [])
        ]
        session.legacy_totals = "invocations" not in document or document.get("legacy_totals", False)
        return session

    # ── Sessão → documento ───────────────────────────────────────────────────

    def __totals_to_document(self, totals: SessionTotals) -> dict[str, Any]:
        """Converte os totais agregados da sessão no seu documento."""
        return {
            "total_messages": totals.total_messages,
            "total_llm_calls": totals.total_llm_calls,
            "tokens_input": totals.tokens_input,
            "tokens_output": totals.tokens_output,
            "total_tokens": totals.total_tokens,
            "inference_time_ms": totals.inference_time_ms,
            "wall_time_ms": totals.wall_time_ms,
        }

    def __message_to_document(self, message: SessionMessage) -> dict[str, Any]:
        """Converte uma mensagem do histórico no seu documento."""
        return {
            "id": message.id,
            "order": message.order,
            "timestamp": message.timestamp.isoformat(),
            "phase": message.phase.value,
            "source": message.source.value,
            "content": message.content,
            "task_id": message.task_id,
            "context_id": message.context_id,
            "tokens_input": message.tokens_input,
            "tokens_output": message.tokens_output,
            "total_tokens": message.total_tokens,
            "inference_time_ms": message.inference_time_ms,
            "model_name": message.model_name,
            "prompt_input": [self.__prompt_message_to_document(message=item) for item in message.prompt_input],
        }

    def __prompt_message_to_document(self, message: Message) -> dict[str, Any]:
        """Converte uma mensagem da conversa enviada ao modelo no seu documento."""
        return {
            "source": message.source.value,
            "text": message.text,
            "creation_timestamp": message.creation_timestamp.isoformat(),
        }

    def __degradation_to_document(self, degradation: SessionDegradation) -> dict[str, Any]:
        """Converte uma degradação registrada no seu documento."""
        return {
            "limit": degradation.limit.value,
            "phase": degradation.phase.value,
            "task_id": degradation.task_id,
            "description": degradation.description,
            "occurred_at": degradation.occurred_at.isoformat(),
        }

    def __invocation_to_document(self, invocation: LLMInvocation) -> dict[str, Any]:
        """Converte uma invocação ao modelo no seu documento."""
        return {
            "id": invocation.id,
            "phase": invocation.phase.value,
            "task_id": invocation.task_id,
            "context_id": invocation.context_id,
            "model_name": invocation.model_name,
            "provider": invocation.provider.value,
            "started_at": invocation.started_at.isoformat(),
            "outcome": invocation.outcome.value,
            "duration_ms": invocation.duration_ms,
            "tokens_input": invocation.tokens_input,
            "tokens_output": invocation.tokens_output,
            "finish_reason": invocation.finish_reason,
            "provider_response_id": invocation.provider_response_id,
        }

    def __failure_to_document(self, failure: SessionFailure | None) -> dict[str, Any] | None:
        """Converte a falha estruturada no seu documento, ou nulo quando não houve falha."""
        if failure is None:
            return None
        return {
            "reason": failure.reason.value,
            "phase": failure.phase.value,
            "description": failure.description,
            "occurred_at": failure.occurred_at.isoformat(),
            "limit": failure.limit.value if failure.limit is not None else None,
            "task_id": failure.task_id,
            "pending_criteria_ids": list(failure.pending_criteria_ids),
        }

    # ── Documento → sessão ───────────────────────────────────────────────────

    def __optional_provider(self, document: dict[str, Any]) -> ModelProviderEnum | None:
        """Reconstrói o provedor da sessão, ausente em documentos anteriores ao registro."""
        if document.get("provider") is None:
            return None
        return self.__enum_from_document(
            document=document, key="provider", container=_SESSION_CONTAINER, enum_type=ModelProviderEnum
        )

    def __invocation_from_document(self, document: dict[str, Any]) -> LLMInvocation:
        """Reconstrói uma invocação ao modelo a partir do documento."""
        return LLMInvocation(
            id=self.__required(document=document, key="id", container=_INVOCATION_CONTAINER),
            phase=self.__enum_from_document(
                document=document, key="phase", container=_INVOCATION_CONTAINER, enum_type=ThinkingPhaseEnum
            ),
            task_id=self.__required(document=document, key="task_id", container=_INVOCATION_CONTAINER),
            context_id=self.__required(document=document, key="context_id", container=_INVOCATION_CONTAINER),
            model_name=self.__required(document=document, key="model_name", container=_INVOCATION_CONTAINER),
            provider=self.__enum_from_document(
                document=document, key="provider", container=_INVOCATION_CONTAINER, enum_type=ModelProviderEnum
            ),
            started_at=self.__datetime_from_document(
                document=document, key="started_at", container=_INVOCATION_CONTAINER
            ),
            outcome=self.__enum_from_document(
                document=document, key="outcome", container=_INVOCATION_CONTAINER, enum_type=InvocationOutcomeEnum
            ),
            duration_ms=self.__required(document=document, key="duration_ms", container=_INVOCATION_CONTAINER),
            tokens_input=self.__required(document=document, key="tokens_input", container=_INVOCATION_CONTAINER),
            tokens_output=self.__required(document=document, key="tokens_output", container=_INVOCATION_CONTAINER),
            finish_reason=self.__required(document=document, key="finish_reason", container=_INVOCATION_CONTAINER),
            provider_response_id=self.__required(
                document=document, key="provider_response_id", container=_INVOCATION_CONTAINER
            ),
        )

    def __failure_from_optional_document(self, document: dict[str, Any] | None) -> SessionFailure | None:
        """Reconstrói a falha estruturada, ausente em documentos anteriores ao registro."""
        if document is None:
            return None

        has_limit = self.__required(document=document, key="limit", container=_FAILURE_CONTAINER) is not None
        return SessionFailure(
            reason=self.__enum_from_document(
                document=document, key="reason", container=_FAILURE_CONTAINER, enum_type=SessionFailureReasonEnum
            ),
            phase=self.__enum_from_document(
                document=document, key="phase", container=_FAILURE_CONTAINER, enum_type=ThinkingPhaseEnum
            ),
            description=self.__required(document=document, key="description", container=_FAILURE_CONTAINER),
            occurred_at=self.__datetime_from_document(
                document=document, key="occurred_at", container=_FAILURE_CONTAINER
            ),
            limit=(
                self.__enum_from_document(
                    document=document, key="limit", container=_FAILURE_CONTAINER, enum_type=BudgetLimitEnum
                )
                if has_limit
                else None
            ),
            task_id=self.__required(document=document, key="task_id", container=_FAILURE_CONTAINER),
            pending_criteria_ids=tuple(
                self.__required(document=document, key="pending_criteria_ids", container=_FAILURE_CONTAINER)
            ),
        )

    def __totals_from_document(self, document: dict[str, Any]) -> SessionTotals:
        """Reconstrói os totais agregados a partir do documento."""
        return SessionTotals(
            total_messages=self.__required(document=document, key="total_messages", container=_TOTALS_CONTAINER),
            total_llm_calls=self.__required(document=document, key="total_llm_calls", container=_TOTALS_CONTAINER),
            tokens_input=self.__required(document=document, key="tokens_input", container=_TOTALS_CONTAINER),
            tokens_output=self.__required(document=document, key="tokens_output", container=_TOTALS_CONTAINER),
            inference_time_ms=self.__required(
                document=document, key="inference_time_ms", container=_TOTALS_CONTAINER
            ),
            wall_time_ms=self.__required(document=document, key="wall_time_ms", container=_TOTALS_CONTAINER),
        )

    def __message_from_document(self, document: dict[str, Any]) -> SessionMessage:
        """Reconstrói uma mensagem do histórico a partir do documento."""
        return SessionMessage(
            id=self.__required(document=document, key="id", container=_MESSAGE_CONTAINER),
            order=self.__required(document=document, key="order", container=_MESSAGE_CONTAINER),
            timestamp=self.__datetime_from_document(
                document=document, key="timestamp", container=_MESSAGE_CONTAINER
            ),
            phase=self.__enum_from_document(
                document=document, key="phase", container=_MESSAGE_CONTAINER, enum_type=ThinkingPhaseEnum
            ),
            source=self.__enum_from_document(
                document=document, key="source", container=_MESSAGE_CONTAINER, enum_type=MessageSourceEnum
            ),
            content=self.__required(document=document, key="content", container=_MESSAGE_CONTAINER),
            task_id=self.__required(document=document, key="task_id", container=_MESSAGE_CONTAINER),
            context_id=self.__required(document=document, key="context_id", container=_MESSAGE_CONTAINER),
            tokens_input=self.__required(document=document, key="tokens_input", container=_MESSAGE_CONTAINER),
            tokens_output=self.__required(document=document, key="tokens_output", container=_MESSAGE_CONTAINER),
            inference_time_ms=self.__required(
                document=document, key="inference_time_ms", container=_MESSAGE_CONTAINER
            ),
            model_name=self.__required(document=document, key="model_name", container=_MESSAGE_CONTAINER),
            prompt_input=tuple(
                self.__prompt_message_from_document(document=item) for item in document.get("prompt_input", [])
            ),
        )

    def __prompt_message_from_document(self, document: dict[str, Any]) -> Message:
        """Reconstrói uma mensagem da conversa enviada ao modelo a partir do documento."""
        return Message(
            creation_timestamp=self.__datetime_from_document(
                document=document, key="creation_timestamp", container=_PROMPT_INPUT_CONTAINER
            ),
            text=self.__required(document=document, key="text", container=_PROMPT_INPUT_CONTAINER),
            source=self.__enum_from_document(
                document=document, key="source", container=_PROMPT_INPUT_CONTAINER, enum_type=MessageSourceEnum
            ),
        )

    def __degradation_from_document(self, document: dict[str, Any]) -> SessionDegradation:
        """Reconstrói uma degradação registrada a partir do documento."""
        return SessionDegradation(
            limit=self.__enum_from_document(
                document=document, key="limit", container=_DEGRADATION_CONTAINER, enum_type=BudgetLimitEnum
            ),
            phase=self.__enum_from_document(
                document=document, key="phase", container=_DEGRADATION_CONTAINER, enum_type=ThinkingPhaseEnum
            ),
            task_id=self.__required(document=document, key="task_id", container=_DEGRADATION_CONTAINER),
            description=self.__required(document=document, key="description", container=_DEGRADATION_CONTAINER),
            occurred_at=self.__datetime_from_document(
                document=document, key="occurred_at", container=_DEGRADATION_CONTAINER
            ),
        )

    # ── Leitura defensiva ────────────────────────────────────────────────────

    def __required(self, document: dict[str, Any], key: str, container: str) -> Any:
        """Devolve o valor de uma chave obrigatória do documento.

        Raises:
            ValueError: Quando a chave não está presente.
        """
        if key not in document:
            raise ValueError(f"Chave obrigatória '{key}' ausente no documento de {container}.")
        return document[key]

    def __enum_from_document(
        self,
        document: dict[str, Any],
        key: str,
        container: str,
        enum_type: type[TEnum],
    ) -> TEnum:
        """Reconstrói um enum a partir do valor persistido.

        Raises:
            ValueError: Quando a chave falta ou o valor não pertence ao enum.
        """
        raw_value = self.__required(document=document, key=key, container=container)
        try:
            return enum_type(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"Campo '{key}' do documento de {container} tem valor inválido "
                f"para {enum_type.__name__}: '{raw_value}'."
            ) from exc

    def __datetime_from_document(self, document: dict[str, Any], key: str, container: str) -> datetime:
        """Reconstrói uma data a partir do valor persistido.

        Raises:
            ValueError: Quando a chave falta, o valor não é ISO-8601 ou não tem fuso horário.
        """
        raw_value = self.__required(document=document, key=key, container=container)
        try:
            parsed_value = datetime.fromisoformat(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Campo '{key}' do documento de {container} deve ser uma data ISO-8601. Valor: '{raw_value}'."
            ) from exc

        if parsed_value.tzinfo is None:
            raise ValueError(
                f"Campo '{key}' do documento de {container} deve declarar fuso horário. Valor: '{raw_value}'."
            )
        return parsed_value
