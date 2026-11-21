from src.domain.enums.output_defect_enum import OutputDefectEnum


def test_declara_exatamente_os_defeitos_de_saida_tratados() -> None:
    assert {member.value for member in OutputDefectEnum} == {"syntax", "contract", "truncated"}


def test_valores_de_cada_membro() -> None:
    assert OutputDefectEnum.SYNTAX == "syntax"
    assert OutputDefectEnum.CONTRACT == "contract"
    assert OutputDefectEnum.TRUNCATED == "truncated"


def test_e_uma_str_enum() -> None:
    assert isinstance(OutputDefectEnum.SYNTAX, str)


def test_cada_defeito_tem_um_nome_legivel() -> None:
    assert OutputDefectEnum.SYNTAX.label == "erro de sintaxe"
    assert OutputDefectEnum.CONTRACT.label == "violação de contrato"
    assert OutputDefectEnum.TRUNCATED.label == "interrupção por comprimento"
