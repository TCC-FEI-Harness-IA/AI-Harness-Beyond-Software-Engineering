from src.domain.enums.ralph_flow_version_enum import RalphFlowVersionEnum


def test_declara_as_duas_versoes_do_fluxo_ralph() -> None:
    assert {member.value for member in RalphFlowVersionEnum} == {1, 2}


def test_a_versao_1_e_o_planejamento_sem_validacao_e_a_2_o_validado() -> None:
    assert RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION == 1
    assert RalphFlowVersionEnum.VALIDATED_PLANNING == 2
    assert RalphFlowVersionEnum.current() is RalphFlowVersionEnum.VALIDATED_PLANNING
    assert RalphFlowVersionEnum.legacy() is RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION


def test_e_persistida_como_inteiro() -> None:
    assert isinstance(RalphFlowVersionEnum.VALIDATED_PLANNING, int)
    assert RalphFlowVersionEnum(2) is RalphFlowVersionEnum.VALIDATED_PLANNING
