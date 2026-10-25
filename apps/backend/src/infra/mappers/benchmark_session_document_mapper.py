from datetime import datetime
from enum import StrEnum
from typing import Any, TypeVar

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_llm_config import BenchmarkLLMConfig
from src.domain.entities.benchmark.benchmark_mode_summary import BenchmarkModeSummary
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper

_DOCUMENT_ID_KEY = "_id"
_SESSION_CONTAINER = "bateria de benchmark"
_QUESTION_CONTAINER = "questão da bateria"
_OUTCOME_CONTAINER = "desfecho de fluxo da bateria"

TEnum = TypeVar("TEnum", bound=StrEnum)


class BenchmarkSessionDocumentMapper(IBenchmarkSessionDocumentMapper):
    """Data Mapper entre `BenchmarkSession` e o documento persistido (`dict`).

    O documento é JSON puro, com a chave primária `_id` espelhada em `id`, e é o mesmo em
    qualquer backend de armazenamento. Além dos campos de origem, ele traz os valores derivados
    (progresso, tokens, sessões e totais por fluxo) já calculados, para que a API e o WebSocket
    os entreguem prontos; na leitura, os derivados são ignorados e recalculados pela entidade.
    """

    def to_document(self, benchmark_session: BenchmarkSession) -> dict[str, Any]:
        """Converte uma bateria no documento a ser persistido.

        Args:
            benchmark_session: Bateria a ser convertida.

        Returns:
            dict[str, Any]: Documento equivalente à bateria, serializável em JSON.
        """
        config = benchmark_session.llm_config
        return {
            _DOCUMENT_ID_KEY: benchmark_session.id,
            "id": benchmark_session.id,
            "status": benchmark_session.status.value,
            "model_name": config.model_name,
            "provider": config.provider.value,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "max_parallel": benchmark_session.max_parallel,
            "question_count": benchmark_session.question_count,
            "created_at": benchmark_session.created_at.isoformat(),
            "updated_at": benchmark_session.updated_at.isoformat(),
            "finished_at": self.__optional_datetime_to_document(value=benchmark_session.finished_at),
            "wall_time_ms": benchmark_session.wall_time_ms,
            "error": benchmark_session.error,
            "progress": {
                "total": benchmark_session.question_count,
                "pending": benchmark_session.pending_count,
                "running": benchmark_session.running_count,
                "finished": benchmark_session.finished_count,
                "interrupted": benchmark_session.interrupted_count,
            },
            "total_tokens": benchmark_session.total_tokens,
            "session_ids": benchmark_session.session_ids,
            "summary": {
                mode.value: self.__summary_to_document(summary=benchmark_session.summary(mode=mode))
                for mode in BenchmarkInferenceModeEnum
            },
            "questions": [self.__question_to_document(question=question) for question in benchmark_session.questions],
        }

    def from_document(self, document: dict[str, Any]) -> BenchmarkSession:
        """Converte um documento persistido de volta em uma bateria.

        Args:
            document: Documento persistido.

        Returns:
            BenchmarkSession: Bateria equivalente ao documento.

        Raises:
            ValueError: Quando falta uma chave obrigatória, um enum tem valor desconhecido ou uma
                data não é ISO-8601 com fuso horário.
        """
        container = _SESSION_CONTAINER
        return BenchmarkSession(
            id=self.__required(document=document, key=_DOCUMENT_ID_KEY, container=container),
            llm_config=BenchmarkLLMConfig(
                model_name=self.__required(document=document, key="model_name", container=container),
                provider=self.__enum(
                    document=document, key="provider", container=container, enum_type=ModelProviderEnum
                ),
                max_tokens=self.__required(document=document, key="max_tokens", container=container),
                temperature=self.__required(document=document, key="temperature", container=container),
            ),
            max_parallel=self.__required(document=document, key="max_parallel", container=container),
            status=self.__enum(
                document=document, key="status", container=container, enum_type=BenchmarkSessionStatusEnum
            ),
            created_at=self.__datetime(document=document, key="created_at", container=container),
            updated_at=self.__datetime(document=document, key="updated_at", container=container),
            finished_at=(
                self.__datetime(document=document, key="finished_at", container=container)
                if self.__required(document=document, key="finished_at", container=container) is not None
                else None
            ),
            wall_time_ms=self.__required(document=document, key="wall_time_ms", container=container),
            error=self.__required(document=document, key="error", container=container),
            questions=[
                self.__question_from_document(document=item)
                for item in self.__required(document=document, key="questions", container=container)
            ],
        )

    # ── Bateria → documento ──────────────────────────────────────────────────

    def __summary_to_document(self, summary: BenchmarkModeSummary) -> dict[str, Any]:
        """Converte os totais de um fluxo no seu documento."""
        return {
            "executed": summary.executed,
            "correct": summary.correct,
            "wrong": summary.wrong,
            "failures": summary.failures,
            "accuracy": summary.accuracy,
            "total_tokens": summary.total_tokens,
            "duration_seconds": summary.duration_seconds,
        }

    def __question_to_document(self, question: BenchmarkQuestionRun) -> dict[str, Any]:
        """Converte a execução de uma questão no seu documento."""
        return {
            "question_id": question.question_id,
            "expected_alternative": question.expected_alternative,
            "status": question.status.value,
            "current_mode": question.current_mode.value if question.current_mode is not None else None,
            "current_tokens": question.current_tokens,
            "total_tokens": question.total_tokens,
            "simple": self.__outcome_to_document(outcome=question.simple),
            "ralph": self.__outcome_to_document(outcome=question.ralph),
        }

    def __outcome_to_document(self, outcome: BenchmarkFlowOutcome | None) -> dict[str, Any] | None:
        """Converte o desfecho de um fluxo no seu documento, ou nulo quando ainda não há."""
        if outcome is None:
            return None
        return {
            "mode": outcome.mode.value,
            "session_id": outcome.session_id,
            "selected_alternative": outcome.selected_alternative,
            "is_correct": outcome.is_correct,
            "error": outcome.error,
            "duration_seconds": outcome.duration_seconds,
            "total_tokens": outcome.total_tokens,
        }

    def __optional_datetime_to_document(self, value: datetime | None) -> str | None:
        """Converte uma data opcional em ISO-8601."""
        return value.isoformat() if value is not None else None

    # ── Documento → bateria ──────────────────────────────────────────────────

    def __question_from_document(self, document: dict[str, Any]) -> BenchmarkQuestionRun:
        """Reconstrói a execução de uma questão a partir do documento."""
        container = _QUESTION_CONTAINER
        current_mode = self.__required(document=document, key="current_mode", container=container)
        return BenchmarkQuestionRun(
            question_id=self.__required(document=document, key="question_id", container=container),
            expected_alternative=self.__required(document=document, key="expected_alternative", container=container),
            status=self.__enum(
                document=document, key="status", container=container, enum_type=BenchmarkQuestionStatusEnum
            ),
            simple=self.__outcome_from_document(document=self.__required(document, "simple", container)),
            ralph=self.__outcome_from_document(document=self.__required(document, "ralph", container)),
            current_mode=(
                self.__enum(
                    document=document, key="current_mode", container=container, enum_type=BenchmarkInferenceModeEnum
                )
                if current_mode is not None
                else None
            ),
            current_tokens=self.__required(document=document, key="current_tokens", container=container),
        )

    def __outcome_from_document(self, document: dict[str, Any] | None) -> BenchmarkFlowOutcome | None:
        """Reconstrói o desfecho de um fluxo, ausente enquanto o fluxo não terminou."""
        if document is None:
            return None
        container = _OUTCOME_CONTAINER
        return BenchmarkFlowOutcome(
            mode=self.__enum(document=document, key="mode", container=container, enum_type=BenchmarkInferenceModeEnum),
            session_id=self.__required(document=document, key="session_id", container=container),
            selected_alternative=self.__required(document=document, key="selected_alternative", container=container),
            is_correct=self.__required(document=document, key="is_correct", container=container),
            error=self.__required(document=document, key="error", container=container),
            duration_seconds=self.__required(document=document, key="duration_seconds", container=container),
            total_tokens=self.__required(document=document, key="total_tokens", container=container),
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

    def __enum(self, document: dict[str, Any], key: str, container: str, enum_type: type[TEnum]) -> TEnum:
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

    def __datetime(self, document: dict[str, Any], key: str, container: str) -> datetime:
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
