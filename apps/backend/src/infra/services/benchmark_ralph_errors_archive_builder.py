import io
import json
import re
import zipfile
from dataclasses import dataclass
from typing import Any

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")
_QUESTION_FILE = "questao.json"
_EXECUTION_FILE = "execucao-ralph-loop.json"
_EXPECTED_ANSWER_FILE = "resposta-esperada.json"
_JSON_ENCODING = "utf-8"


@dataclass(frozen=True)
class BenchmarkArchive:
    """Arquivo ZIP gerado para download.

    Attributes:
        filename: Nome sugerido para o arquivo.
        content: Bytes do ZIP.
        media_type: Tipo de mídia do conteúdo.
    """

    filename: str
    content: bytes
    media_type: str = "application/zip"


class BenchmarkRalphErrorsArchiveBuilder:
    """Empacota os erros do Ralph Loop de uma bateria em um ZIP, com uma pasta por questão."""

    def __init__(self, session_mapper: ISessionDocumentMapper) -> None:
        """Inicializa o construtor.

        Args:
            session_mapper: Conversor de `Session` no mesmo documento persistido.
        """
        self.session_mapper: ISessionDocumentMapper = session_mapper

    def build(self, benchmark_session_id: str, errors: list[BenchmarkRalphError]) -> BenchmarkArchive:
        """Monta o ZIP com `questao.json`, `execucao-ralph-loop.json` e `resposta-esperada.json` por questão.

        Args:
            benchmark_session_id: Identificador da bateria exportada.
            errors: Erros do Ralph Loop, uma pasta para cada.

        Returns:
            BenchmarkArchive: Arquivo pronto para download.
        """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for error in errors:
                folder = f"questao-{self.__safe_name(error.question_id)}"
                archive.writestr(f"{folder}/{_QUESTION_FILE}", self.__dump(self.__question_document(error)))
                archive.writestr(
                    f"{folder}/{_EXECUTION_FILE}",
                    self.__dump(self.__execution_document(benchmark_session_id=benchmark_session_id, error=error)),
                )
                archive.writestr(
                    f"{folder}/{_EXPECTED_ANSWER_FILE}", self.__dump(self.__expected_answer_document(error))
                )
        return BenchmarkArchive(
            filename=f"benchmark-session-{self.__safe_name(benchmark_session_id)}-ralph-loop-errors.zip",
            content=buffer.getvalue(),
        )

    def __question_document(self, error: BenchmarkRalphError) -> dict[str, Any]:
        """Identificador, enunciado e alternativas; `None` quando a questão saiu do dataset."""
        question = error.question
        return {
            "id": error.question_id,
            "statement": question.statement if question is not None else None,
            "options": question.options if question is not None else None,
        }

    def __execution_document(self, benchmark_session_id: str, error: BenchmarkRalphError) -> dict[str, Any]:
        """Desfecho da questão no Ralph Loop e a sessão completa que o produziu."""
        outcome = error.outcome
        return {
            "benchmark_session_id": benchmark_session_id,
            "question_id": error.question_id,
            "outcome": {
                "mode": outcome.mode.value,
                "session_id": outcome.session_id,
                "selected_alternative": outcome.selected_alternative,
                "is_correct": outcome.is_correct,
                "error": outcome.error,
                "duration_seconds": outcome.duration_seconds,
                "total_tokens": outcome.total_tokens,
            },
            "session": self.session_mapper.to_document(session=error.session) if error.session is not None else None,
        }

    def __expected_answer_document(self, error: BenchmarkRalphError) -> dict[str, Any]:
        """Alternativa correta, com a letra e o texto quando o dataset ainda a conhece."""
        question = error.question
        return {
            "question_id": error.question_id,
            "alternative": error.expected_alternative,
            "text": question.options.get(error.expected_alternative) if question is not None else None,
            "answer": question.expected_answer if question is not None else None,
        }

    def __dump(self, document: dict[str, Any]) -> bytes:
        """Serializa o documento em JSON legível, preservando acentos."""
        return json.dumps(document, ensure_ascii=False, indent=2).encode(_JSON_ENCODING)

    def __safe_name(self, value: str) -> str:
        """Troca por `_` o que não serve em nome de arquivo ou de cabeçalho HTTP."""
        return _UNSAFE_NAME_CHARS.sub("_", value)
