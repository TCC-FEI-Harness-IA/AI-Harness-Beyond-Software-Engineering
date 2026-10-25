import logging
from pathlib import Path

import pytest

from src.infra.config.settings import Settings
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from tests.doubles.benchmark_factories import questao
from tests.doubles.fake_settings import FakeSettings


def _provider(questoes: Path, instrucao: Path | None = None) -> FileBenchmarkQuestionProvider:
    return FileBenchmarkQuestionProvider(
        settings=FakeSettings(
            ralph_benchmark_questions_path=str(questoes),
            ralph_benchmark_prompt_path=str(instrucao or questoes / "prompt.md"),
        ),
        logger=logging.getLogger("teste"),
    )


def _gravar(diretorio: Path, nome: str, enunciado: str | None = None, gabarito: str = "A) um") -> None:
    pasta = diretorio / nome
    pasta.mkdir(parents=True)
    (pasta / "enunciado.md").write_text(enunciado or questao().statement, encoding="utf-8")
    (pasta / "alternativa_correta.md").write_text(gabarito, encoding="utf-8")


def test_dataset_real_tem_quinze_questoes_validas_em_ordem() -> None:
    provider = FileBenchmarkQuestionProvider(settings=Settings(), logger=logging.getLogger("teste"))

    questoes = provider.list_questions()

    assert len(questoes) == 15
    assert [item.id for item in questoes] == sorted(item.id for item in questoes)
    assert all(len(item.options) == 5 for item in questoes)
    assert "RESPOSTA_FINAL: LETRA" in provider.answer_instruction()


def test_carrega_as_pastas_ordenadas_e_ignora_arquivos(tmp_path: Path) -> None:
    _gravar(tmp_path, "Q2", gabarito="B) dois")
    _gravar(tmp_path, "Q1")
    (tmp_path / "README.md").write_text("documentação", encoding="utf-8")
    provider = _provider(tmp_path)

    questoes = provider.list_questions()

    assert [item.id for item in questoes] == ["Q1", "Q2"]
    assert questoes[1].expected_alternative == "B"
    assert questoes[1].expected_answer == "B) dois"


def test_le_o_disco_uma_unica_vez(tmp_path: Path) -> None:
    _gravar(tmp_path, "Q1")
    provider = _provider(tmp_path)
    provider.list_questions()
    _gravar(tmp_path, "Q2")

    assert [item.id for item in provider.list_questions()] == ["Q1"]


def test_diretorio_inexistente_e_recusado(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="não encontrado"):
        _provider(tmp_path / "nada").list_questions()


def test_diretorio_sem_questoes_e_recusado(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Nenhuma questão"):
        _provider(tmp_path).list_questions()


def test_questao_sem_gabarito_e_recusada(tmp_path: Path) -> None:
    (tmp_path / "Q1").mkdir()
    (tmp_path / "Q1" / "enunciado.md").write_text(questao().statement, encoding="utf-8")

    with pytest.raises(ValueError, match="incompleta em Q1"):
        _provider(tmp_path).list_questions()


def test_questao_sem_as_cinco_alternativas_e_recusada(tmp_path: Path) -> None:
    _gravar(tmp_path, "Q1", enunciado="Pergunta\n\nA) um\nB) dois")

    with pytest.raises(ValueError, match="Alternativas ou gabarito"):
        _provider(tmp_path).list_questions()


def test_gabarito_fora_do_formato_e_recusado(tmp_path: Path) -> None:
    _gravar(tmp_path, "Q1", gabarito="a resposta é A")

    with pytest.raises(ValueError, match="Alternativas ou gabarito"):
        _provider(tmp_path).list_questions()


def test_gabarito_com_texto_diferente_e_recusado(tmp_path: Path) -> None:
    _gravar(tmp_path, "Q1", gabarito="A) outro texto")

    with pytest.raises(ValueError, match="Texto do gabarito"):
        _provider(tmp_path).list_questions()


def test_instrucao_e_lida_uma_vez_sem_espacos_nas_bordas(tmp_path: Path) -> None:
    instrucao = tmp_path / "prompt.md"
    instrucao.write_text("\n  Responda.  \n", encoding="utf-8")
    provider = _provider(tmp_path, instrucao)

    assert provider.answer_instruction() == "Responda."
    instrucao.write_text("Outra", encoding="utf-8")
    assert provider.answer_instruction() == "Responda."


def test_instrucao_inexistente_e_recusada(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="não encontrada"):
        _provider(tmp_path, tmp_path / "nada.md").answer_instruction()


def test_instrucao_vazia_e_recusada(tmp_path: Path) -> None:
    instrucao = tmp_path / "prompt.md"
    instrucao.write_text("   ", encoding="utf-8")

    with pytest.raises(ValueError, match="vazia"):
        _provider(tmp_path, instrucao).answer_instruction()
