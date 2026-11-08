import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider

_PLACEHOLDERS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: {"user_question"},
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"user_question", "max_tasks"},
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: {"user_question"},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {
        "task_description", "task_acceptance_criteria", "learnings", "previous_attempts", "results_under_review"
    },
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: {
        "preliminary_result", "task_acceptance_criteria", "learnings", "revision_proposal"
    },
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: {"task_description", "approved_result", "task_history", "learnings"},
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: {
        "stored_results", "general_acceptance_criteria", "learnings", "result_revisions"
    },
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: {
        "user_question", "unmet_criteria", "global_verification_feedback", "stored_results",
        "next_task_number", "max_tasks", "learnings", "result_revisions"
    },
    ThinkingPhaseEnum.C3_FINAL_ANSWER: {"stored_results", "general_acceptance_criteria", "learnings"},
}
_FASES_COM_APRENDIZADOS_PONTUAIS = [
    ThinkingPhaseEnum.B1_TASK_RESOLUTION,
    ThinkingPhaseEnum.B2_TASK_VERIFICATION,
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION,
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
    ThinkingPhaseEnum.C3_FINAL_ANSWER,
]


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))


def test_os_nove_templates_existem_no_diretorio_configurado() -> None:
    provider = _provider()

    for fase in _PLACEHOLDERS_POR_FASE:
        assert provider.get(phase=fase).strip()


def test_todo_template_exige_saida_em_json() -> None:
    provider = _provider()

    for fase in _PLACEHOLDERS_POR_FASE:
        template = provider.get(phase=fase)
        assert "## Output format" in template
        assert "JSON" in template


def test_cada_template_declara_exatamente_os_placeholders_que_o_fluxo_entrega() -> None:
    provider = _provider()

    for fase, placeholders in _PLACEHOLDERS_POR_FASE.items():
        renderizado = provider.render(
            phase=fase,
            variables={placeholder: f"<{placeholder}>" for placeholder in placeholders},
        )
        for placeholder in placeholders:
            assert f"<{placeholder}>" in renderizado
        assert "{{" not in renderizado


_FASES_DE_VERIFICACAO = [ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION]
_FASES_DE_PLANEJAMENTO = [ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING]


def test_templates_de_verificacao_exigem_uma_avaliacao_exata_por_criterio() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase).lower()
        assert "exactly one evaluation" in template
        assert "do not omit" in template
        assert "do not repeat" in template
        assert "invent identifiers" in template


def test_templates_de_verificacao_exigem_pendencias_iguais_as_avaliacoes_negativas() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase)
        assert "`met` equal to `false`" in template
        assert "`unmet_criteria_ids` must contain exactly" in template
        assert "`approved` only when" in template


def test_templates_de_planejamento_informam_o_teto_de_tarefas_do_lote() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        renderizado = provider.render(
            phase=fase,
            variables={
                "user_question": "q",
                "unmet_criteria": "u",
                "global_verification_feedback": "f",
                "stored_results": "s",
                "next_task_number": "2",
                "max_tasks": "7",
                "learnings": "l",
                "result_revisions": "r",
            },
        )
        assert "at most 7" in renderizado
        assert "do not merge" in renderizado


def test_template_de_aprendizados_do_planejamento_manda_preservar_o_que_chama_a_atencao() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "values" in template and "units of measurement" in template
    assert "options" in template
    assert "formulas" in template
    assert "constraints" in template
    assert "literally" in template


def test_template_de_aprendizados_do_planejamento_proibe_resolver_a_pergunta() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "do not solve" in template
    assert "no conclusion" in template


def test_template_de_aprendizados_do_planejamento_devolve_lista_vazia_quando_nada_se_aplica() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS)

    assert "empty list" in template
    assert '{"learnings": [' in template


# ── Área de Key Learnings em todo template de B e C ─────────────────


def test_todo_template_de_b_e_c_tem_a_area_de_aprendizados_pontuais_com_todos_os_aprendizados() -> None:
    provider = _provider()

    for fase in _FASES_COM_APRENDIZADOS_PONTUAIS:
        template = provider.get(phase=fase)
        assert "## Key Learnings" in template, fase
        area = template.split("## Key Learnings", 1)[1].split("\n## ", 1)[0]
        assert "{{learnings}}" in area, fase


def test_a_area_de_aprendizados_pontuais_vem_antes_do_formato_de_saida() -> None:
    provider = _provider()

    for fase in _FASES_COM_APRENDIZADOS_PONTUAIS:
        template = provider.get(phase=fase)
        assert template.index("## Key Learnings") < template.index("## Output format"), fase


def test_os_templates_de_planejamento_inicial_nao_tem_a_area_de_aprendizados() -> None:
    provider = _provider()

    # A.1, A.2 e A.3 rodam antes de existir qualquer aprendizado: a área não teria conteúdo.
    for fase in (
        ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        ThinkingPhaseEnum.A3_PLANNING_LEARNINGS,
    ):
        assert "{{learnings}}" not in provider.get(phase=fase)


def test_os_validadores_nao_tratam_os_aprendizados_como_criterio_nem_como_resultado() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase).lower()
        assert "are not criteria" in template, fase
    assert "do not count as coverage" in provider.get(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION).lower()


def test_a_resposta_final_continua_construida_so_com_os_resultados_armazenados() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).lower()

    assert "do not replace the stored results" in template
    assert "introduce new facts that are not in the stored results" in template


def test_a_extracao_de_aprendizados_nao_repete_os_ja_registrados() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).lower()

    assert "do not repeat" in template


# ── Regras de redação das tarefas em A.2 e C.2 ──────────────────────────────


def test_templates_de_planejamento_nao_pedem_mais_entradas_e_saida_das_tarefas() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = provider.get(phase=fase)
        assert "**inputs**" not in template, fase
        assert "expected_input" not in template, fase
        assert "expected_output" not in template, fase


def test_templates_de_planejamento_exigem_criterios_complementares_entre_si() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "complementary, never mutually exclusive" in template, fase
        assert "meet all of them at the same time" in template, fase
        assert '"answer only the option"' in template, fase


def test_templates_de_planejamento_exigem_resultado_com_explicacao() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "accompanied by the explanation" in template, fase
        assert "never the result alone" in template, fase
        assert "formulas used" in template and "conventions adopted" in template, fase
        assert "include an acceptance criterion that checks it" in template, fase


def test_template_a2_orienta_decomposicao_parcimoniosa_e_por_condicoes() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION).lower().split())

    assert "smallest possible number of tasks" in template
    assert "never by option" in template
    assert "avoid bureaucratic or redundant tasks" in template


def test_template_b4_proibe_metadados_da_tarefa_e_do_validador_nos_aprendizados() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).lower().split())

    assert "content of the problem" in template
    assert "mentions of the task itself" in template
    assert "approval (`approved`) or rejection (`reproved`) verdict" in template
    assert "control data, operational metadata" not in template


# ── B.4 — Resultados parciais da tarefa aprovada ────────────────────────────


def _b4() -> str:
    return " ".join(_provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).split())


def test_template_b4_recebe_o_material_da_extracao_em_areas_delimitadas_e_nao_da_conversa() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION)

    assert "<approved_result>\n{{approved_result}}\n</approved_result>" in template
    assert "<task_history>\n{{task_history}}\n</task_history>" in template
    assert "its own context window" in _b4()
    assert "context above" not in _b4()
    # O histórico é material da extração: as áreas da tarefa vêm antes das instruções.
    assert template.index("{{task_history}}") < template.index("## Instructions")


def test_template_b4_exige_registrar_todo_resultado_parcial_novo_com_significado_autonomo() -> None:
    template = _b4().lower()

    assert "record every new partial result from the approved result" in template
    assert "without the previous history" in template
    assert "the simplicity of a conclusion does not justify omitting it" in template
    assert "go through the approved result conclusion by conclusion" in template


def test_template_b4_define_o_que_preservar_para_valores_classificacoes_e_relacoes() -> None:
    template = _b4().lower()

    assert "**values:** preserve the quantity" in template
    assert "the value, the unit of measurement and the relevant conditions" in template
    assert "**classifications:** identify the statement" in template
    assert "its classification" in template and "a brief reason" in template
    assert "**relations:** preserve the formula or relation and the hypotheses needed" in template


def test_template_b4_distingue_o_fato_compacto_da_breve_explicacao_sem_copiar_a_resolucao() -> None:
    template = _b4()

    assert "**compact fact**" in template and "**brief explanation**" in template
    assert "Do not copy the complete resolution" in template
    assert '"Statement I is true: C ⊆ A implies A ∩ C = C, by distributivity."' in template


def test_template_b4_prioriza_a_conclusao_aprovada_e_descarta_valores_refutados() -> None:
    template = _b4().lower()

    assert "prioritize the finally approved conclusion" in template
    assert "refuted, corrected or replaced" in template
    assert "are not current learnings" in template


def test_template_b4_proibe_instrucoes_criterios_vereditos_relatos_e_duplicatas() -> None:
    template = _b4().lower()

    assert "task instructions" in template
    assert "acceptance criteria" in template
    assert "verdicts" in template
    assert "reports of the execution process" in template
    assert "rewordings of facts already in **key learnings**" in template


def test_template_b4_so_admite_lista_vazia_sem_fato_novo() -> None:
    template = _b4()

    assert '`{"learnings": []}` **only**' in template
    assert "no new fact" in template
    assert "re-establishes none of the facts already in **Key Learnings**" in template


def test_templates_orientam_avaliacao_relativa_por_eliminacao_sem_hiper_literalismo() -> None:
    provider = _provider()

    a1 = " ".join(provider.get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA).lower().split())
    assert "best fit by elimination" in a1
    assert "approve or discard them in advance" in a1

    for fase in (
        ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
        ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
    ):
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "elimination" in template, fase
        assert "100% literal" in template or "hyper-litera" in template, fase


def test_templates_de_planejamento_proibem_pre_calculo_e_pedem_escopo_afirmativo() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "pre-calculate" in template, fase
        assert "affirmative and delimiting" in template, fase
        assert "is restricted exclusively to" in template, fase


def test_templates_de_planejamento_exigem_que_a_ultima_tarefa_conclua_a_grandeza_final() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "last task" in template, fase
        assert "final quantity" in template, fase


def test_templates_de_verificacao_pedem_decision_por_ultimo_no_json() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        formato = provider.get(phase=fase).split("## Output format", 1)[1]
        assert formato.index('"criteria_evaluation"') < formato.index('"unmet_criteria_ids"') < formato.index(
            '"decision"'
        ), fase


def test_template_b1_delimita_tentativas_anteriores_antes_do_formato_de_saida() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)
    assert "## Previous attempts at this task" in template
    assert "<previous_attempts>" in template
    assert template.index("{{previous_attempts}}") < template.index("## Output format")


def test_template_b4_extrai_do_historico_delimitado_e_nao_do_contexto_acima() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION)
    normalizado = " ".join(template.lower().split())

    assert "## Task history" in template
    assert "<task_history>" in template
    assert "context above" not in normalizado
    assert "do not continue" in normalizado
    assert template.index("{{task_history}}") < template.index("## Output format")


def test_template_de_resolucao_pede_a_conclusao_separada_do_raciocinio() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).split())

    assert "In the `conclusion` field" in template
    assert '"conclusion":' in template


def test_template_de_planejamento_adicional_traz_o_prompt_original_antes_dos_resultados() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)

    assert template.index("## Original Prompt\n") < template.index("{{user_question}}")
    assert template.index("{{user_question}}") < template.index("## Results already stored")
    assert "its statement and the conclusion" in template


def test_a1_define_o_idioma_da_resposta_pelo_idioma_da_pergunta() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA).split())

    assert "It is the language in which the question is written" in template
    assert "never defines the language of the final answer" in template


def test_c1_e_c3_nao_tratam_resultados_em_outro_idioma_como_lacuna() -> None:
    provider = _provider()

    c1 = " ".join(provider.get(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION).split())
    c3 = " ".join(provider.get(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).split())
    assert "do not make a language criterion unmet" in c1
    assert "translating is presentation, not new reasoning" in c3


def test_os_templates_estao_em_ingles() -> None:
    provider = _provider()

    for fase in _PLACEHOLDERS_POR_FASE:
        template = provider.get(phase=fase)
        for termo in ("## Instruções", "Aprendizados Pontuais", "Responda", "tarefa", "critério"):
            assert termo not in template, (fase, termo)
