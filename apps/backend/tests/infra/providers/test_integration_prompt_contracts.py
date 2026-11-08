"""Coerência conjunta dos nove templates e das mensagens de recuperação (thinking 07).

Cada etapa anterior testou o seu trecho. Estes testes leem os templates como um conjunto: procuram
instruções que se contradizem entre fases, saídas de exemplo incompatíveis com o contrato do parser
e vazamento dos oráculos da matriz de regressões integradas. São contratos de prompt, não prova de
que um modelo real os obedece.
"""
import ast
import json
import logging
import re
from pathlib import Path

import pytest

import src.application.phases.base_thinking_phase as base_phase
import src.application.usecases.ralph_thinking_usecase as usecase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_FASES_COM_TEMPLATE = [
    Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
    Phase.A4_PLANNING_LEARNINGS,
    Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
    Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, Phase.C3_FINAL_ANSWER,
]
_RAIZ_TESTES = Path(__file__).resolve().parents[2]
_MATRIZ = json.loads((_RAIZ_TESTES / "fixtures" / "integration_regressions_v1.json").read_text(encoding="utf-8"))
_SRC = _RAIZ_TESTES.parent / "src"

# Comandos que, se voltassem a qualquer template ou mensagem de recuperação, contradiriam a política
# única de evidência (etapa 04) ou o protocolo de revisão (etapa 05).
_COMANDOS_CONTRADITORIOS = [
    r"consider (it|the criterion) met (if|when) the result explicitly selects",
    r"as long as an option is (chosen|selected)",
    r"(closest|nearest) (option|value)[^.]{0,60}\b(always|automatically) (valid|met|approved|accepted)",
    r"(never|do not|don't) (reopen|revisit|re-?examine|re-?investigate|question) (an? |any |the )?"
    r"(approved|stored|previous|earlier) (result|task|conclusion)",
    r"(most recent|latest|later) (result|task|conclusion) (always )?(prevails|wins|overrides|replaces)",
    r"fix(ing)? exactly these points",
]


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger("teste.integracao.templates"))


def _normalizado(texto: str) -> str:
    return " ".join(texto.split())


def _template(fase: Phase) -> str:
    return _normalizado(_provider().get(phase=fase))


def _secao(template_bruto: str, titulo: str) -> str:
    conteudo = template_bruto.split(f"## {titulo}\n", 1)[1]
    return _normalizado(re.split(r"\n## ", conteudo, maxsplit=1)[0])


def _mensagens_internas() -> list[str]:
    """Instruções fixas que o código acrescenta aos prompts: recuperação e retentativa de B.1."""
    return [
        *base_phase._CORRECTION_BY_DEFECT.values(),
        base_phase._PLANNING_RECOVERY_INSTRUCTIONS,
        usecase._RETRY_INSTRUCTION_CONTENT,
    ]


@pytest.mark.parametrize("fase", _FASES_COM_TEMPLATE, ids=lambda fase: fase.value)
def test_nenhum_template_reintroduz_aprovacao_por_escolha_ou_blindagem_do_aprovado(fase: Phase) -> None:
    texto = _template(fase).lower()

    for padrao in _COMANDOS_CONTRADITORIOS:
        assert re.search(padrao, texto) is None, (fase, padrao)


def test_mensagens_de_recuperacao_e_retentativa_nao_reintroduzem_comandos_contraditorios() -> None:
    for mensagem in _mensagens_internas():
        texto = _normalizado(mensagem).lower()
        for padrao in _COMANDOS_CONTRADITORIOS:
            assert re.search(padrao, texto) is None, (mensagem[:60], padrao)


def test_c2_concilia_evitar_retrabalho_com_investigar_defeito_concreto_de_resultado_aprovado() -> None:
    c2 = _template(Phase.C2_ADDITIONAL_PLANNING)

    assert "Avoid redoing an established investigation without a reason" in c2
    assert "a previously approved result may be investigated when the feedback gives a concrete reason" in c2
    assert "verified before it takes effect" in c2
    assert "Do not reopen unrelated resolved work" in c2


def test_formato_de_saida_de_c2_numera_a_partir_da_proxima_tarefa_da_sessao() -> None:
    renderizado = _provider().render(
        phase=Phase.C2_ADDITIONAL_PLANNING,
        variables={"user_question": "q", "unmet_criteria": "u", "global_verification_feedback": "f",
                   "stored_results": "s", "result_revisions": "r", "learnings": "l", "max_tasks": "3",
                   "next_task_number": "4"},
    )
    formato = _secao(renderizado, "Output format")

    assert '"id": "T4"' in formato and '"T4-AC1"' in formato
    assert '"id": "T1"' not in formato and "T1-AC1" not in formato


def test_formato_de_saida_de_a2_documenta_depends_on_opcional_sem_campo_de_revisao() -> None:
    formato = _secao(_provider().get(phase=Phase.A2_TASK_DECOMPOSITION), "Output format")

    assert '"depends_on": ["T1"]' in formato
    assert "optional" in formato
    assert "review" not in formato


def test_c2_descreve_os_resultados_recebidos_como_vigentes() -> None:
    area = _secao(_provider().get(phase=Phase.C2_ADDITIONAL_PLANNING), "Results already stored")

    assert "current" in area
    assert "superseded" in area and "awaiting revalidation" in area


@pytest.mark.parametrize("fase", [Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING],
                         ids=lambda fase: fase.value)
def test_registro_de_revisoes_explica_que_resultado_confirmado_continua_vigente(fase: Phase) -> None:
    area = _secao(_provider().get(phase=fase), "Revision record")

    assert "confirmed" in area
    assert "remain" in area and "current" in area
    assert "recency" in area


def test_c1_nao_deixa_uma_confirmacao_aprovada_ser_tratada_como_contradicao_pendente() -> None:
    c1 = _template(Phase.C1_GLOBAL_VERIFICATION)

    assert "does not override an earlier one merely by being more recent" in c1
    assert "A result confirmed by an approved review stays current" in c1


def test_aproximacao_e_igualdade_falsa_tem_o_mesmo_tratamento_em_b2_c1_e_c3() -> None:
    b2 = _template(Phase.B2_TASK_VERIFICATION)
    c1 = _template(Phase.C1_GLOBAL_VERIFICATION)
    c3 = _template(Phase.C3_FINAL_ANSWER)

    for texto in (b2, c1):
        assert "a numerical difference alone is not a defect" in texto
        assert "no rule that selecting an option passes" in texto
    assert "without asserting a false equality" in b2
    assert "never write that they correspond exactly" in c1
    assert "never write that they are equal" in c3
    assert "do not re-validate it with stricter standards than the approval applied" in c3
    assert "Do not repair, recalculate or reconcile results here" in c3


def test_c3_e_apresentacao_e_toda_revisao_acontece_antes_dela() -> None:
    c2 = _template(Phase.C2_ADDITIONAL_PLANNING)
    c3 = _template(Phase.C3_FINAL_ANSWER)

    assert "the only way the session changes which results are current" in c2
    assert "superseded conclusions and rejected attempts are not part of them" in c3
    assert "resolve a residual conflict between results" in c3
    assert "{{result_revisions}}" not in c3


def test_matriz_integrada_tem_os_doze_casos_ligados_a_testes_existentes() -> None:
    casos = _MATRIZ["cases"]
    modulo = _RAIZ_TESTES / "application" / "usecases" / "test_ralph_five_fronts_integration.py"
    funcoes = {no.name for no in ast.walk(ast.parse(modulo.read_text(encoding="utf-8")))
               if isinstance(no, ast.AsyncFunctionDef | ast.FunctionDef)}

    assert _MATRIZ["version"] == 1
    assert len(casos) == len({caso["name"] for caso in casos}) == 12
    frentes = {frente for caso in casos for frente in caso["fronts"]}
    assert frentes == {"structure_recovery", "learnings", "planning", "validation", "synthesis"}
    for caso in casos:
        assert caso["question"] and caso["original_defect"] and caso["programmatic_behavior"], caso["name"]
        assert caso["review_checks"], caso["name"]
        assert set(caso["deterministic_tests"]) <= funcoes, caso["name"]


def _oraculos() -> list[str]:
    textos = []
    for caso in _MATRIZ["cases"]:
        oraculo = caso["reference_oracle"]
        textos.extend(oraculo.get("values", []))
        textos.extend(oraculo[chave] for chave in ("derivation", "conclusion", "defect") if chave in oraculo)
    return textos


@pytest.mark.parametrize("fase", _FASES_COM_TEMPLATE, ids=lambda fase: fase.value)
def test_oraculos_da_matriz_nao_aparecem_nos_templates_de_producao(fase: Phase) -> None:
    template = _provider().get(phase=fase)

    for oraculo in _oraculos():
        assert oraculo not in template, (fase, oraculo)
    for numero in ("17,76", "17.76", "1,2985", "42/64", "21/64", "−420", "-420", "175", "m(v+u)", "54 min"):
        assert numero not in template, (fase, numero)


def test_codigo_de_producao_nao_le_a_matriz_nem_campos_de_benchmark_no_nucleo() -> None:
    servicos = _SRC / "domain" / "services"
    nucleo = [*(_SRC / "application" / "phases").glob("*.py"), _SRC / "application" / "usecases" /
              "ralph_thinking_usecase.py", servicos / "task_queue.py", servicos / "learnings_memory.py",
              servicos / "results_ledger.py"]

    for arquivo in nucleo:
        codigo = arquivo.read_text(encoding="utf-8")
        assert "integration_regressions" not in codigo, arquivo.name
        assert "fixtures" not in codigo, arquivo.name
        assert "question.options" not in codigo and "expected_answer" not in codigo, arquivo.name
