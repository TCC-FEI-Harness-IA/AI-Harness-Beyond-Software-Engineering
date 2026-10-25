from dataclasses import asdict

import pytest

from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum


def test_sessao_comum_tem_flag_falsa_e_demais_campos_nulos() -> None:
    fields = asdict(BenchmarkDetails())
    assert fields.pop("is_banchmark") is False
    assert all(value is None for value in fields.values())


def test_benchmark_guarda_valores_e_enum() -> None:
    details = BenchmarkDetails(is_banchmark=True, question_name="Q1", inference_mode=BenchmarkInferenceModeEnum.RALPH)
    assert details.question_name == "Q1"
    assert details.inference_mode is BenchmarkInferenceModeEnum.RALPH


@pytest.mark.parametrize("value", [None, 1, "false"])
def test_flag_nao_booleana_e_recusada(value) -> None:
    with pytest.raises(ValueError, match="booleano"):
        BenchmarkDetails(is_banchmark=value)


def test_sessao_comum_nao_aceita_dados_de_benchmark() -> None:
    with pytest.raises(ValueError, match="nulos"):
        BenchmarkDetails(question_name="Q1")
