from src.domain.errors.prompt_template_not_found_error import PromptTemplateNotFoundError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(PromptTemplateNotFoundError, RalphError)


def test_carrega_os_atributos_informados() -> None:
    erro = PromptTemplateNotFoundError(template_name="a1_general_criteria", path="src/infra/templates")

    assert erro.template_name == "a1_general_criteria"
    assert erro.path == "src/infra/templates"


def test_mensagem_referencia_o_template_e_o_caminho() -> None:
    erro = PromptTemplateNotFoundError(template_name="a1_general_criteria", path="src/infra/templates")

    assert "a1_general_criteria" in str(erro)
    assert "src/infra/templates" in str(erro)
