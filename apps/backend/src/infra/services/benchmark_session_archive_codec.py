import io
import json
import re
import zipfile
from datetime import datetime
from typing import Any

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from src.domain.entities.session.session import Session
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkArchive

ARCHIVE_FORMAT = "ralph-benchmark-session"
ARCHIVE_VERSION = 1

MANIFEST_FILE = "manifest.json"
BENCHMARK_SESSION_FILE = "bateria.json"
QUESTIONS_DIRECTORY = "questoes"
STATEMENT_FILE = "enunciado.json"
EXPECTED_ANSWER_FILE = "resposta-esperada.json"
SIMPLE_EXECUTION_FILE = "execucao-simples.json"
RALPH_EXECUTION_FILE = "execucao-ralph-loop.json"

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
"""Tamanho máximo do ZIP recebido na importação."""
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
"""Soma máxima dos arquivos descompactados, contra *zip bombs*."""
MAX_ENTRIES = 50_000

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_FOLDER_PATTERN = re.compile(rf"^{QUESTIONS_DIRECTORY}/[A-Za-z0-9_.-]+$")
_JSON_ENCODING = "utf-8"


class BenchmarkSessionArchiveCodec:
    """Converte uma bateria completa em ZIP padronizado e de volta.

    Estrutura do ZIP (versão 1)::

        manifest.json                     formato, versão e índice das questões
        bateria.json                      documento completo da BenchmarkSession
        questoes/0001-<questao>/
            enunciado.json                enunciado original e alternativas do dataset
            resposta-esperada.json        gabarito (letra, texto e alternativa completa)
            execucao-simples.json         desfecho e sessão completa da inferência simples
            execucao-ralph-loop.json      desfecho e sessão completa do Ralph Loop

    Os documentos de bateria e de sessão são os mesmos que a persistência grava, então a
    importação reconstrói exatamente o que foi exportado.
    """

    def __init__(
        self,
        benchmark_mapper: IBenchmarkSessionDocumentMapper,
        session_mapper: ISessionDocumentMapper,
    ) -> None:
        """Inicializa o codec.

        Args:
            benchmark_mapper: Conversor de `BenchmarkSession` no documento persistido.
            session_mapper: Conversor de `Session` no documento persistido.
        """
        self.benchmark_mapper: IBenchmarkSessionDocumentMapper = benchmark_mapper
        self.session_mapper: ISessionDocumentMapper = session_mapper

    # ── Exportação ───────────────────────────────────────────────────────────

    def build(self, bundle: BenchmarkSessionBundle, exported_at: datetime) -> BenchmarkArchive:
        """Monta o ZIP da bateria completa.

        Args:
            bundle: Bateria com o conteúdo de cada questão.
            exported_at: Instante da exportação, registrado no manifesto.

        Returns:
            BenchmarkArchive: Arquivo pronto para download.
        """
        benchmark_session = bundle.benchmark_session
        buffer = io.BytesIO()
        manifest_questions: list[dict[str, Any]] = []
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                BENCHMARK_SESSION_FILE,
                self.__dump(self.benchmark_mapper.to_document(benchmark_session=benchmark_session)),
            )
            for index, item in enumerate(bundle.items, start=1):
                run = item.run
                folder = f"{QUESTIONS_DIRECTORY}/{index:04d}-{self.__safe_name(run.question_id)}"
                archive.writestr(f"{folder}/{STATEMENT_FILE}", self.__dump(self.__statement_document(item)))
                archive.writestr(f"{folder}/{EXPECTED_ANSWER_FILE}", self.__dump(self.__expected_document(item)))
                archive.writestr(
                    f"{folder}/{SIMPLE_EXECUTION_FILE}",
                    self.__dump(
                        self.__execution_document(benchmark_session.id, run, "simple", run.simple, item.simple_session)
                    ),
                )
                archive.writestr(
                    f"{folder}/{RALPH_EXECUTION_FILE}",
                    self.__dump(
                        self.__execution_document(benchmark_session.id, run, "ralph", run.ralph, item.ralph_session)
                    ),
                )
                manifest_questions.append(
                    {
                        "question_id": run.question_id,
                        "folder": folder,
                        "has_statement": item.question is not None,
                        "simple_session_id": item.simple_session.id if item.simple_session is not None else None,
                        "ralph_session_id": item.ralph_session.id if item.ralph_session is not None else None,
                    }
                )
            archive.writestr(
                MANIFEST_FILE,
                self.__dump(
                    {
                        "format": ARCHIVE_FORMAT,
                        "version": ARCHIVE_VERSION,
                        "exported_at": exported_at.isoformat(),
                        "benchmark_session_id": benchmark_session.id,
                        "benchmark_session_file": BENCHMARK_SESSION_FILE,
                        "question_count": len(bundle.items),
                        "session_count": len(bundle.sessions),
                        "files": {
                            "statement": STATEMENT_FILE,
                            "expected_answer": EXPECTED_ANSWER_FILE,
                            "simple_execution": SIMPLE_EXECUTION_FILE,
                            "ralph_execution": RALPH_EXECUTION_FILE,
                        },
                        "questions": manifest_questions,
                    }
                ),
            )
        return BenchmarkArchive(filename=archive_filename(benchmark_session.id), content=buffer.getvalue())

    def __statement_document(self, item: BenchmarkSessionBundleItem) -> dict[str, Any]:
        """Enunciado original e alternativas; nulos quando o dataset não conhece mais a questão."""
        question = item.question
        return {
            "id": item.run.question_id,
            "subject": item.run.subject,
            "statement": question.statement if question is not None else None,
            "options": question.options if question is not None else None,
        }

    def __expected_document(self, item: BenchmarkSessionBundleItem) -> dict[str, Any]:
        """Gabarito registrado na bateria, com o texto quando o dataset ainda o conhece."""
        question = item.question
        alternative = item.run.expected_alternative
        return {
            "question_id": item.run.question_id,
            "alternative": alternative,
            "text": question.options.get(alternative) if question is not None else None,
            "answer": question.expected_answer if question is not None else None,
        }

    def __execution_document(
        self,
        benchmark_session_id: str,
        run: BenchmarkQuestionRun,
        mode: str,
        outcome: BenchmarkFlowOutcome | None,
        session: Session | None,
    ) -> dict[str, Any]:
        """Desfecho de um fluxo e a sessão completa que o produziu."""
        return {
            "benchmark_session_id": benchmark_session_id,
            "question_id": run.question_id,
            "mode": mode,
            "outcome": (
                {
                    "mode": outcome.mode.value,
                    "session_id": outcome.session_id,
                    "selected_alternative": outcome.selected_alternative,
                    "is_correct": outcome.is_correct,
                    "error": outcome.error,
                    "duration_seconds": outcome.duration_seconds,
                    "total_tokens": outcome.total_tokens,
                }
                if outcome is not None
                else None
            ),
            "session": self.session_mapper.to_document(session=session) if session is not None else None,
        }

    # ── Importação ───────────────────────────────────────────────────────────

    def read(self, content: bytes) -> BenchmarkSessionBundle:
        """Lê e valida um ZIP exportado por `build`.

        Args:
            content: Bytes do ZIP.

        Returns:
            BenchmarkSessionBundle: Bateria com o conteúdo de cada questão.

        Raises:
            InvalidBenchmarkArchiveError: Quando o ZIP não é válido, excede os limites ou tem
                documentos ausentes, malformados ou inconsistentes.
        """
        if len(content) > MAX_ARCHIVE_BYTES:
            raise InvalidBenchmarkArchiveError(f"o ZIP excede o limite de {MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB.")
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise InvalidBenchmarkArchiveError("o arquivo enviado não é um ZIP válido.") from exc

        with archive:
            self.__check_limits(archive=archive)
            manifest = self.__load_json(archive, MANIFEST_FILE)
            self.__check_manifest(manifest=manifest)

            benchmark_document = self.__load_json(archive, manifest["benchmark_session_file"])
            try:
                benchmark_session = self.benchmark_mapper.from_document(document=benchmark_document)
            except (ValueError, KeyError, TypeError) as exc:
                raise InvalidBenchmarkArchiveError(f"documento da bateria inválido ({exc}).") from exc
            self.__check_id(benchmark_session.id, "bateria")
            if manifest["benchmark_session_id"] != benchmark_session.id:
                raise InvalidBenchmarkArchiveError("o manifesto aponta para outra bateria.")

            entries = manifest["questions"]
            if not isinstance(entries, list) or [
                entry.get("question_id") if isinstance(entry, dict) else None for entry in entries
            ] != [run.question_id for run in benchmark_session.questions]:
                raise InvalidBenchmarkArchiveError("o índice de questões do manifesto não corresponde à bateria.")

            items = [
                self.__read_item(archive=archive, run=run, folder=entry.get("folder"))
                for run, entry in zip(benchmark_session.questions, entries, strict=True)
            ]
        return BenchmarkSessionBundle(benchmark_session=benchmark_session, items=items)

    def __check_limits(self, archive: zipfile.ZipFile) -> None:
        """Recusa ZIPs com entradas demais ou que descompactam além do limite."""
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise InvalidBenchmarkArchiveError(f"o ZIP tem mais de {MAX_ENTRIES} arquivos.")
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise InvalidBenchmarkArchiveError("o conteúdo descompactado do ZIP excede o limite permitido.")

    def __check_manifest(self, manifest: dict[str, Any]) -> None:
        """Confere formato, versão e campos obrigatórios do manifesto."""
        if manifest.get("format") != ARCHIVE_FORMAT:
            raise InvalidBenchmarkArchiveError(
                f"o manifesto não é de uma bateria exportada (formato esperado: '{ARCHIVE_FORMAT}')."
            )
        if manifest.get("version") != ARCHIVE_VERSION:
            raise InvalidBenchmarkArchiveError(
                f"versão de arquivo não suportada: {manifest.get('version')!r} (suportada: {ARCHIVE_VERSION})."
            )
        for key in ("benchmark_session_id", "benchmark_session_file", "questions"):
            if key not in manifest:
                raise InvalidBenchmarkArchiveError(f"o manifesto não tem o campo obrigatório '{key}'.")
        if manifest["benchmark_session_file"] != BENCHMARK_SESSION_FILE:
            raise InvalidBenchmarkArchiveError("o manifesto aponta para um documento de bateria desconhecido.")

    def __read_item(
        self, archive: zipfile.ZipFile, run: BenchmarkQuestionRun, folder: Any
    ) -> BenchmarkSessionBundleItem:
        """Lê a pasta de uma questão: enunciado e as sessões dos dois fluxos."""
        if not isinstance(folder, str) or not _FOLDER_PATTERN.fullmatch(folder):
            raise InvalidBenchmarkArchiveError(f"pasta inválida para a questão '{run.question_id}'.")
        return BenchmarkSessionBundleItem(
            run=run,
            question=self.__read_question(archive=archive, run=run, folder=folder),
            simple_session=self.__read_session(archive, f"{folder}/{SIMPLE_EXECUTION_FILE}", run.question_id),
            ralph_session=self.__read_session(archive, f"{folder}/{RALPH_EXECUTION_FILE}", run.question_id),
        )

    def __read_question(
        self, archive: zipfile.ZipFile, run: BenchmarkQuestionRun, folder: str
    ) -> BenchmarkQuestion | None:
        """Reconstrói a questão original, quando o arquivo traz enunciado e alternativas."""
        document = self.__load_json(archive, f"{folder}/{STATEMENT_FILE}")
        statement, options = document.get("statement"), document.get("options")
        if statement is None or options is None:
            return None
        if not isinstance(statement, str) or not isinstance(options, dict):
            raise InvalidBenchmarkArchiveError(f"enunciado inválido para a questão '{run.question_id}'.")
        try:
            return BenchmarkQuestion(
                id=run.question_id,
                statement=statement,
                options={str(key): str(value) for key, value in options.items()},
                expected_alternative=run.expected_alternative,
                subject=run.subject,
            )
        except ValueError as exc:
            raise InvalidBenchmarkArchiveError(str(exc)) from exc

    def __read_session(self, archive: zipfile.ZipFile, name: str, question_id: str) -> Session | None:
        """Reconstrói a sessão de um fluxo, ou `None` quando o fluxo não deixou sessão."""
        document = self.__load_json(archive, name)
        if document.get("question_id") != question_id:
            raise InvalidBenchmarkArchiveError(f"'{name}' pertence a outra questão.")
        session_document = document.get("session")
        if session_document is None:
            return None
        if not isinstance(session_document, dict):
            raise InvalidBenchmarkArchiveError(f"sessão inválida em '{name}'.")
        try:
            session = self.session_mapper.from_document(document=session_document)
        except (ValueError, KeyError, TypeError) as exc:
            raise InvalidBenchmarkArchiveError(f"sessão inválida em '{name}' ({exc}).") from exc
        self.__check_id(session.id, "sessão")
        return session

    def __load_json(self, archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
        """Lê um documento JSON do ZIP, exigindo um objeto."""
        try:
            raw = archive.read(name)
        except KeyError as exc:
            raise InvalidBenchmarkArchiveError(f"o ZIP não contém '{name}'.") from exc
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise InvalidBenchmarkArchiveError(f"não foi possível ler '{name}' do ZIP.") from exc
        try:
            document = json.loads(raw.decode(_JSON_ENCODING))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidBenchmarkArchiveError(f"'{name}' não é um JSON UTF-8 válido.") from exc
        if not isinstance(document, dict):
            raise InvalidBenchmarkArchiveError(f"'{name}' deveria conter um objeto JSON.")
        return document

    def __check_id(self, value: str, label: str) -> None:
        """Recusa identificadores que não poderiam ser persistidos com segurança."""
        if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
            raise InvalidBenchmarkArchiveError(f"identificador de {label} inválido: '{value}'.")

    # ── Apoio ────────────────────────────────────────────────────────────────

    def __dump(self, document: dict[str, Any]) -> bytes:
        """Serializa o documento em JSON legível, preservando acentos."""
        return json.dumps(document, ensure_ascii=False, indent=2).encode(_JSON_ENCODING)

    @staticmethod
    def __safe_name(value: str) -> str:
        """Troca por `_` o que não serve em nome de arquivo ou de cabeçalho HTTP."""
        return _UNSAFE_NAME_CHARS.sub("_", value)


def archive_filename(benchmark_session_id: str) -> str:
    """Nome sugerido para o ZIP da bateria completa."""
    return f"benchmark-session-{_UNSAFE_NAME_CHARS.sub('_', benchmark_session_id)}.zip"
