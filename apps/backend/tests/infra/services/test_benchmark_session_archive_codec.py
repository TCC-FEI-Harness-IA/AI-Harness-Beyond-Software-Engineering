import io
import json
import zipfile
from dataclasses import replace
from collections.abc import Callable
from typing import Any

import pytest

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.services import benchmark_session_archive_codec as codec_module
from src.infra.services.benchmark_session_archive_codec import BenchmarkSessionArchiveCodec, archive_filename
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho, questao
from tests.doubles.session_factories import sessao_ralph

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH
_PASTA_Q1 = "questoes/0001-Q1"
_PASTA_Q2 = "questoes/0002-Q2"


def _codec() -> BenchmarkSessionArchiveCodec:
    return BenchmarkSessionArchiveCodec(
        benchmark_mapper=BenchmarkSessionDocumentMapper(), session_mapper=SessionDocumentMapper()
    )


def _bateria() -> BenchmarkSession:
    sessao = bateria("Q1", "Q2")
    sessao.questions[0].subject = "BIOLOGIA"
    for questao_id, simples, ralph in (("Q1", "q1_s", "q1_r"), ("Q2", "q2_s", None)):
        sessao.start_flow(question_id=questao_id, mode=_SIMPLES, at=CRIADO_EM)
        sessao.record_outcome(question_id=questao_id, outcome=desfecho(mode=_SIMPLES, session_id=simples), at=CRIADO_EM)
        sessao.start_flow(question_id=questao_id, mode=_RALPH, at=CRIADO_EM)
        sessao.record_outcome(
            question_id=questao_id,
            outcome=desfecho(mode=_RALPH, correto=False, erro=None if ralph else "falhou", session_id=ralph),
            at=CRIADO_EM,
        )
        sessao.finish_question(question_id=questao_id, at=CRIADO_EM)
    sessao.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=CRIADO_EM, wall_time_ms=10)
    return sessao


def _pacote() -> BenchmarkSessionBundle:
    benchmark = _bateria()
    return BenchmarkSessionBundle(
        benchmark_session=benchmark,
        items=[
            BenchmarkSessionBundleItem(
                run=benchmark.questions[0],
                question=questao("Q1"),
                simple_session=sessao_ralph("q1_s", "Q1"),
                ralph_session=sessao_ralph("q1_r", "Q1"),
            ),
            BenchmarkSessionBundleItem(run=benchmark.questions[1], simple_session=sessao_ralph("q2_s", "Q2")),
        ],
    )


def _zip() -> bytes:
    return _codec().build(bundle=_pacote(), exported_at=CRIADO_EM).content


def _ler(conteudo: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as zip_:
        return {nome: zip_.read(nome) for nome in zip_.namelist()}


def _json(conteudo: bytes, nome: str) -> Any:
    return json.loads(_ler(conteudo)[nome].decode("utf-8"))


def _regravar(conteudo: bytes, alterar: Callable[[dict[str, Any]], None]) -> bytes:
    """Reescreve o ZIP depois de alterar os arquivos (nome → bytes ou documento JSON)."""
    arquivos: dict[str, Any] = _ler(conteudo)
    alterar(arquivos)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as zip_:
        for nome, valor in arquivos.items():
            zip_.writestr(nome, valor if isinstance(valor, bytes) else json.dumps(valor).encode("utf-8"))
    return buffer.getvalue()


def _editar_json(nome: str, alterar: Callable[[Any], Any]) -> Callable[[dict[str, Any]], None]:
    """Altera o documento JSON no lugar; o retorno de `alterar` é ignorado."""

    def editar(arquivos: dict[str, Any]) -> None:
        documento = json.loads(arquivos[nome])
        alterar(documento)
        arquivos[nome] = documento

    return editar


# ── Exportação ───────────────────────────────────────────────────────────────


def test_zip_tem_manifesto_bateria_e_quatro_arquivos_por_questao() -> None:
    arquivo = _codec().build(bundle=_pacote(), exported_at=CRIADO_EM)

    assert arquivo.filename == "benchmark-session-bench_1.zip"
    assert arquivo.media_type == "application/zip"
    assert sorted(_ler(arquivo.content)) == sorted(
        ["manifest.json", "bateria.json"]
        + [
            f"{pasta}/{nome}"
            for pasta in (_PASTA_Q1, _PASTA_Q2)
            for nome in (
                "enunciado.json", "resposta-esperada.json", "execucao-simples.json", "execucao-ralph-loop.json"
            )
        ]
    )


def test_manifesto_identifica_formato_versao_e_indice_das_questoes() -> None:
    manifesto = _json(_zip(), "manifest.json")

    assert manifesto["format"] == "ralph-benchmark-session"
    assert manifesto["version"] == 1
    assert manifesto["exported_at"] == CRIADO_EM.isoformat()
    assert manifesto["benchmark_session_id"] == "bench_1"
    assert manifesto["benchmark_session_file"] == "bateria.json"
    assert manifesto["question_count"] == 2
    assert manifesto["session_count"] == 3
    assert manifesto["questions"] == [
        {"question_id": "Q1", "folder": _PASTA_Q1, "has_statement": True,
         "simple_session_id": "q1_s", "ralph_session_id": "q1_r"},
        {"question_id": "Q2", "folder": _PASTA_Q2, "has_statement": False,
         "simple_session_id": "q2_s", "ralph_session_id": None},
    ]


def test_bateria_e_o_mesmo_documento_persistido() -> None:
    pacote = _pacote()

    documento = _json(_codec().build(bundle=pacote, exported_at=CRIADO_EM).content, "bateria.json")

    assert documento == BenchmarkSessionDocumentMapper().to_document(benchmark_session=pacote.benchmark_session)


def test_enunciado_e_gabarito_vem_do_dataset_ou_ficam_nulos() -> None:
    conteudo = _zip()
    original = questao("Q1")

    assert _json(conteudo, f"{_PASTA_Q1}/enunciado.json") == {
        "id": "Q1", "subject": "BIOLOGIA", "statement": original.statement, "options": original.options,
    }
    assert _json(conteudo, f"{_PASTA_Q1}/resposta-esperada.json") == {
        "question_id": "Q1", "alternative": "A", "text": "um", "answer": "A) um",
    }
    assert _json(conteudo, f"{_PASTA_Q2}/enunciado.json") == {
        "id": "Q2", "subject": None, "statement": None, "options": None,
    }
    assert _json(conteudo, f"{_PASTA_Q2}/resposta-esperada.json") == {
        "question_id": "Q2", "alternative": "A", "text": None, "answer": None,
    }


def test_execucoes_trazem_desfecho_e_sessao_completa_de_cada_fluxo() -> None:
    pacote = _pacote()
    conteudo = _codec().build(bundle=pacote, exported_at=CRIADO_EM).content

    simples = _json(conteudo, f"{_PASTA_Q1}/execucao-simples.json")
    ralph = _json(conteudo, f"{_PASTA_Q1}/execucao-ralph-loop.json")
    sem_sessao = _json(conteudo, f"{_PASTA_Q2}/execucao-ralph-loop.json")

    assert simples["benchmark_session_id"] == "bench_1"
    assert simples["mode"] == "simple"
    assert simples["outcome"]["session_id"] == "q1_s"
    assert simples["session"] == SessionDocumentMapper().to_document(session=pacote.items[0].simple_session)
    assert ralph["mode"] == "ralph"
    assert ralph["session"]["id"] == "q1_r"
    assert sem_sessao["outcome"]["error"] == "falhou"
    assert sem_sessao["session"] is None


def test_fluxo_sem_desfecho_tem_desfecho_nulo() -> None:
    pacote = _pacote()
    pacote.items[1].run.ralph = None

    conteudo = _codec().build(bundle=pacote, exported_at=CRIADO_EM).content

    documento = _json(conteudo, f"{_PASTA_Q2}/execucao-ralph-loop.json")

    assert documento["outcome"] is None
    assert documento["session"] is None


def test_nomes_inseguros_nao_escapam_do_diretorio() -> None:
    assert archive_filename('bench"\r\n/../x') == "benchmark-session-bench____.._x.zip"
    pacote = _pacote()
    pacote.items[0].run.question_id = "../../etc/passwd"

    nomes = _ler(_codec().build(bundle=pacote, exported_at=CRIADO_EM).content)

    assert "questoes/0001-.._.._etc_passwd/enunciado.json" in nomes


# ── Importação ───────────────────────────────────────────────────────────────


def test_le_de_volta_exatamente_o_que_foi_exportado() -> None:
    pacote = _pacote()
    conteudo = _codec().build(bundle=pacote, exported_at=CRIADO_EM).content

    lido = _codec().read(content=conteudo)

    sessoes = SessionDocumentMapper()
    assert lido.benchmark_session == pacote.benchmark_session
    assert [item.run for item in lido.items] == [item.run for item in pacote.items]
    assert [item.question for item in lido.items] == [replace(questao("Q1"), subject="BIOLOGIA"), None]
    assert [sessoes.to_document(session=sessao) for sessao in lido.sessions] == [
        sessoes.to_document(session=sessao) for sessao in pacote.sessions
    ]


def test_recusa_zip_grande_demais(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codec_module, "MAX_ARCHIVE_BYTES", 10)

    with pytest.raises(InvalidBenchmarkArchiveError, match="limite"):
        _codec().read(content=_zip())


def test_recusa_conteudo_que_nao_e_zip() -> None:
    with pytest.raises(InvalidBenchmarkArchiveError, match="não é um ZIP"):
        _codec().read(content=b"nada de zip aqui")


@pytest.mark.parametrize(
    ("limite", "valor", "mensagem"),
    [("MAX_ENTRIES", 3, "arquivos"), ("MAX_UNCOMPRESSED_BYTES", 100, "descompactado")],
)
def test_recusa_zip_com_entradas_ou_tamanho_descompactado_demais(
    monkeypatch: pytest.MonkeyPatch, limite: str, valor: int, mensagem: str
) -> None:
    monkeypatch.setattr(codec_module, limite, valor)

    with pytest.raises(InvalidBenchmarkArchiveError, match=mensagem):
        _codec().read(content=_zip())


def _sem(nome: str) -> Callable[[dict[str, Any]], None]:
    return lambda arquivos: arquivos.pop(nome)


def _definir(nome: str, chave: str, valor: Any) -> Callable[[dict[str, Any]], None]:
    return _editar_json(nome, lambda documento: documento.__setitem__(chave, valor))


def _remover_chave(nome: str, chave: str) -> Callable[[dict[str, Any]], None]:
    return _editar_json(nome, lambda documento: documento.pop(chave))


def _substituir(nome: str, valor: bytes) -> Callable[[dict[str, Any]], None]:
    return lambda arquivos: arquivos.__setitem__(nome, valor)


def _questao_do_manifesto(indice: int, chave: str, valor: Any) -> Callable[[dict[str, Any]], None]:
    return _editar_json("manifest.json", lambda manifesto: manifesto["questions"][indice].__setitem__(chave, valor))


@pytest.mark.parametrize(
    ("alterar", "mensagem"),
    [
        (_sem("manifest.json"), "não contém 'manifest.json'"),
        (_substituir("manifest.json", b"\xff\xfe"), "JSON UTF-8"),
        (_substituir("manifest.json", b"[1, 2]"), "objeto JSON"),
        (_definir("manifest.json", "format", "outro"), "formato esperado"),
        (_definir("manifest.json", "version", 2), "versão de arquivo não suportada"),
        (_remover_chave("manifest.json", "questions"), "campo obrigatório 'questions'"),
        (_definir("manifest.json", "benchmark_session_file", "../x.json"), "documento de bateria desconhecido"),
        (_definir("manifest.json", "benchmark_session_id", "bench_2"), "outra bateria"),
        (_definir("manifest.json", "questions", {"Q1": 1}), "índice de questões"),
        (_definir("manifest.json", "questions", ["Q1", "Q2"]), "índice de questões"),
        (_questao_do_manifesto(1, "question_id", "Q3"), "índice de questões"),
        (_questao_do_manifesto(0, "folder", "../fora"), "pasta inválida"),
        (_questao_do_manifesto(0, "folder", None), "pasta inválida"),
        (_remover_chave("bateria.json", "questions"), "documento da bateria inválido"),
        (_definir("bateria.json", "_id", "../bench"), "identificador de bateria inválido"),
        (_sem(f"{_PASTA_Q1}/execucao-simples.json"), "não contém"),
        (_definir(f"{_PASTA_Q1}/execucao-simples.json", "question_id", "Q2"), "outra questão"),
        (_definir(f"{_PASTA_Q1}/execucao-simples.json", "session", "texto"), "sessão inválida"),
        (
            _editar_json(f"{_PASTA_Q1}/execucao-simples.json", lambda doc: doc["session"].pop("status")),
            "sessão inválida",
        ),
        (
            _editar_json(f"{_PASTA_Q1}/execucao-simples.json", lambda doc: doc["session"].__setitem__("_id", "a/b")),
            "identificador de sessão inválido",
        ),
        (_definir(f"{_PASTA_Q1}/enunciado.json", "options", ["A", "B"]), "enunciado inválido"),
        (_definir(f"{_PASTA_Q1}/enunciado.json", "statement", 7), "enunciado inválido"),
        (_definir(f"{_PASTA_Q1}/enunciado.json", "options", {"B": "dois"}), "Gabarito 'A'"),
    ],
)
def test_recusa_zip_malformado_ou_inconsistente(alterar: Callable[[dict[str, Any]], None], mensagem: str) -> None:
    with pytest.raises(InvalidBenchmarkArchiveError, match=mensagem):
        _codec().read(content=_regravar(_zip(), alterar))


def test_enunciado_sem_alternativas_fica_nulo() -> None:
    conteudo = _regravar(_zip(), _definir(f"{_PASTA_Q1}/enunciado.json", "options", None))

    assert _codec().read(content=conteudo).items[0].question is None


def test_falha_de_leitura_de_uma_entrada_vira_arquivo_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    def ler_corrompido(self, name, pwd=None):
        raise zipfile.BadZipFile("CRC inválido")

    monkeypatch.setattr(zipfile.ZipFile, "read", ler_corrompido)

    with pytest.raises(InvalidBenchmarkArchiveError, match="não foi possível ler"):
        _codec().read(content=_zip())
