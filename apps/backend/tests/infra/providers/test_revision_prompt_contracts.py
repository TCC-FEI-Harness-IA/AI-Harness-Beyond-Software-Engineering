"""Contratos dos templates para a revisão auditável de resultados (thinking 05).

Os testes verificam o que cada prompt instrui e entrega; não provam que um modelo real identifica
o erro, escolhe o veredito correto ou declara toda dependência relevante.
"""
import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider


def _template(phase: Phase) -> str:
    provider = FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.revisao.templates"))
    return " ".join(provider.get(phase=phase).split())


def test_b1_so_propoe_revisao_com_resultados_sob_investigacao_e_sem_presumir_o_errado() -> None:
    b1 = _template(Phase.B1_TASK_RESOLUTION)

    assert b1.index("{{results_under_review}}") < b1.index("## Previous attempts at this task")
    assert "They are claims to check, not established facts" in b1
    assert "without presuming which account is wrong" in b1
    assert "`superseded` only when your investigation identifies the concrete error" in b1
    assert "`confirmed` when the claim withstands the investigation" in b1
    assert "Recency, a different hypothesis or a different wording is not evidence of an error" in b1
    assert "restate in `result` any of its claims that your investigation shows to remain valid" in b1
    assert "When no result is under review, omit the `revision` field" in b1
    assert '"revision": [{"task_id":' in b1


def test_b2_recebe_a_proposta_explicita_e_avalia_o_criterio_de_revisao() -> None:
    b2 = _template(Phase.B2_TASK_VERIFICATION)

    assert b2.index("{{task_acceptance_criteria}}") < b2.index("{{revision_proposal}}")
    assert "(`<task id>-REV`)" in b2
    assert "confirming an earlier result is a valid outcome" in b2
    assert "Approving the task approves the proposal" in b2
    assert "Do not rewrite the proposal or substitute another verdict" in b2


def test_c1_trata_o_registro_de_revisoes_como_historico_e_nao_como_evidencia() -> None:
    c1 = _template(Phase.C1_GLOBAL_VERIFICATION)

    assert c1.index("{{stored_results}}") < c1.index("{{result_revisions}}")
    assert "This is history and status, not evidence" in c1
    assert "name the result to be revalidated" in c1
    assert "does not override an earlier one merely by being more recent" in c1
    assert "Identify the stored results involved by their identifiers" in c1


def test_c2_explica_review_e_depends_on_como_unico_caminho_de_mudanca_de_estado() -> None:
    c2 = _template(Phase.C2_ADDITIONAL_PLANNING)

    assert c2.index("{{stored_results}}") < c2.index("{{result_revisions}}") < c2.index("{{learnings}}")
    assert "They are the only way the session changes which results are current" in c2
    assert "Do not decide the verdict in planning" in c2
    assert "Do not list results that merely differ" in c2
    assert "a superseded result cannot be reviewed again" in c2
    assert "`<task id>-REV`" in c2
    assert "which prior claim it confirms or corrects" in c2
    assert '"review": {"task_ids": ["..."], "reason": "..."}, "depends_on": ["..."]' in c2
    assert "omit them in an ordinary task" in c2


def test_a2_declara_dependencias_so_de_tarefas_anteriores_e_nao_planeja_revisoes() -> None:
    a2 = _template(Phase.A2_TASK_DECOMPOSITION)

    assert "optional `depends_on` field" in a2
    assert "List only earlier tasks of this plan" in a2
    assert '"review"' not in a2


def test_b4_registra_so_fatos_vigentes_sem_relatar_a_revisao() -> None:
    b4 = _template(Phase.B4_LEARNINGS_EXTRACTION)

    assert "Key Learnings show only current facts" in b4
    assert "never as a report about the review" in b4


def test_c3_nao_recebe_o_registro_de_revisoes() -> None:
    assert "{{result_revisions}}" not in _template(Phase.C3_FINAL_ANSWER)
