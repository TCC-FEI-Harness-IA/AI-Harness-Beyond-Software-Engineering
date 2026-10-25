import io
import json
import zipfile

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkRalphErrorsArchiveBuilder
from tests.doubles.benchmark_factories import desfecho, questao
from tests.doubles.session_factories import sessao_ralph

_RALPH = BenchmarkInferenceModeEnum.RALPH


def _erro(identificador: str = "Q1", com_questao: bool = True, com_sessao: bool = True) -> BenchmarkRalphError:
    return BenchmarkRalphError(
        question_id=identificador,
        expected_alternative="A",
        outcome=desfecho(mode=_RALPH, correto=False, session_id="sess_1" if com_sessao else None),
        question=questao(identificador) if com_questao else None,
        session=sessao_ralph("sess_1", identificador) if com_sessao else None,
    )


def _abrir(conteudo: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(conteudo))


def _json(arquivo: zipfile.ZipFile, nome: str) -> dict:
    return json.loads(arquivo.read(nome).decode("utf-8"))


def test_zip_tem_uma_pasta_por_questao_com_os_tres_arquivos() -> None:
    construtor = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper())

    arquivo = construtor.build(benchmark_session_id="bench_1", errors=[_erro("Q1"), _erro("Q2")])

    assert arquivo.filename == "benchmark-session-bench_1-ralph-loop-errors.zip"
    assert arquivo.media_type == "application/zip"
    with _abrir(arquivo.content) as zip_:
        assert sorted(zip_.namelist()) == [
            f"questao-{item}/{nome}"
            for item in ("Q1", "Q2")
            for nome in ("execucao-ralph-loop.json", "questao.json", "resposta-esperada.json")
        ]


def test_questao_traz_identificador_enunciado_e_alternativas() -> None:
    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build("bench_1", [_erro()])

    with _abrir(arquivo.content) as zip_:
        documento = _json(zip_, "questao-Q1/questao.json")

    esperada = questao("Q1")
    assert documento == {"id": "Q1", "statement": esperada.statement, "options": esperada.options}


def test_execucao_traz_o_desfecho_e_a_sessao_completa_do_ralph() -> None:
    erro = _erro()
    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build("bench_1", [erro])

    with _abrir(arquivo.content) as zip_:
        documento = _json(zip_, "questao-Q1/execucao-ralph-loop.json")

    assert documento["benchmark_session_id"] == "bench_1"
    assert documento["question_id"] == "Q1"
    assert documento["outcome"] == {
        "mode": "ralph", "session_id": "sess_1", "selected_alternative": "A", "is_correct": False,
        "error": None, "duration_seconds": 1.5, "total_tokens": 10,
    }
    assert documento["session"] == SessionDocumentMapper().to_document(session=erro.session)
    assert documento["session"]["final_answer"] == "RESPOSTA_FINAL: B"
    assert documento["session"]["messages"][0]["content"] == "Pergunta com acentuação"


def test_resposta_esperada_traz_letra_texto_e_alternativa_completa() -> None:
    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build("bench_1", [_erro()])

    with _abrir(arquivo.content) as zip_:
        documento = _json(zip_, "questao-Q1/resposta-esperada.json")

    assert documento == {"question_id": "Q1", "alternative": "A", "text": "um", "answer": "A) um"}


def test_questao_e_sessao_ausentes_viram_nulos_mantendo_o_que_foi_registrado() -> None:
    erro = _erro(com_questao=False, com_sessao=False)

    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build("bench_1", [erro])

    with _abrir(arquivo.content) as zip_:
        assert _json(zip_, "questao-Q1/questao.json") == {"id": "Q1", "statement": None, "options": None}
        assert _json(zip_, "questao-Q1/execucao-ralph-loop.json")["session"] is None
        assert _json(zip_, "questao-Q1/resposta-esperada.json") == {
            "question_id": "Q1", "alternative": "A", "text": None, "answer": None,
        }


def test_nomes_de_pasta_e_de_arquivo_nao_escapam_do_diretorio() -> None:
    erro = _erro("../../etc/passwd")

    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build(
        'bench"\r\n/../x', [erro]
    )

    assert arquivo.filename == "benchmark-session-bench____.._x-ralph-loop-errors.zip"
    with _abrir(arquivo.content) as zip_:
        assert {nome.split("/")[0] for nome in zip_.namelist()} == {"questao-.._.._etc_passwd"}
