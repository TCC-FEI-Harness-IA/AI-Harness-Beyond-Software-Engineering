import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider

_PLACEHOLDERS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: {"user_question"},
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"user_question", "max_tasks"},
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: {"user_question"},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {"task_description", "task_acceptance_criteria", "learnings"},
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: {"preliminary_result", "task_acceptance_criteria", "learnings"},
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: {"learnings"},
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: {"stored_results", "general_acceptance_criteria", "learnings"},
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: {
        "unmet_criteria", "stored_results", "next_task_number", "max_tasks", "learnings"
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
        assert "## Formato de saída" in template
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
        assert "exatamente uma avaliação" in template
        assert "não omita" in template
        assert "não repita" in template
        assert "invente identificadores" in template


def test_templates_de_verificacao_exigem_pendencias_iguais_as_avaliacoes_negativas() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase)
        assert "`met` igual a `false`" in template
        assert "`unmet_criteria_ids` deve conter exatamente" in template
        assert "`approved` somente quando" in template


def test_templates_de_planejamento_informam_o_teto_de_tarefas_do_lote() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        renderizado = provider.render(
            phase=fase,
            variables={
                "user_question": "q",
                "unmet_criteria": "u",
                "stored_results": "s",
                "next_task_number": "2",
                "max_tasks": "7",
                "learnings": "l",
            },
        )
        assert "no máximo 7 tarefas" in renderizado
        assert "não funda" in renderizado


def test_template_de_aprendizados_do_planejamento_manda_preservar_o_que_chama_a_atencao() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "valores" in template and "unidades de medida" in template
    assert "alternativas" in template
    assert "fórmulas" in template
    assert "restrições" in template
    assert "literalmente" in template


def test_template_de_aprendizados_do_planejamento_proibe_resolver_a_pergunta() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "não resolva" in template
    assert "nenhuma conclusão" in template


def test_template_de_aprendizados_do_planejamento_devolve_lista_vazia_quando_nada_se_aplica() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS)

    assert "lista vazia" in template
    assert '{"learnings": [' in template


# ── Área de Aprendizados Pontuais em todo template de B e C ─────────────────


def test_todo_template_de_b_e_c_tem_a_area_de_aprendizados_pontuais_com_todos_os_aprendizados() -> None:
    provider = _provider()

    for fase in _FASES_COM_APRENDIZADOS_PONTUAIS:
        template = provider.get(phase=fase)
        assert "## Aprendizados Pontuais" in template, fase
        area = template.split("## Aprendizados Pontuais", 1)[1].split("\n## ", 1)[0]
        assert "{{learnings}}" in area, fase


def test_a_area_de_aprendizados_pontuais_vem_antes_do_formato_de_saida() -> None:
    provider = _provider()

    for fase in _FASES_COM_APRENDIZADOS_PONTUAIS:
        template = provider.get(phase=fase)
        assert template.index("## Aprendizados Pontuais") < template.index("## Formato de saída"), fase


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
        assert "não são critérios" in template, fase
    assert "não contam como cobertura" in provider.get(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION).lower()


def test_a_resposta_final_continua_construida_so_com_os_resultados_armazenados() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).lower()

    assert "não substituem os resultados armazenados" in template
    assert "introduzir fatos novos que não estejam nos resultados armazenados" in template


def test_a_extracao_de_aprendizados_nao_repete_os_ja_registrados() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).lower()

    assert "não repita" in template


# ── Regras de redação das tarefas em A.2 e C.2 ──────────────────────────────


def test_templates_de_planejamento_nao_pedem_mais_entradas_e_saida_das_tarefas() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = provider.get(phase=fase)
        assert "**entradas**" not in template, fase
        assert "expected_input" not in template, fase
        assert "expected_output" not in template, fase


def test_templates_de_planejamento_exigem_criterios_complementares_entre_si() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "complementares, nunca mutuamente exclusivos" in template, fase
        assert "atenda a todos eles ao mesmo tempo" in template, fase
        assert '"responda somente a alternativa"' in template, fase


def test_templates_de_planejamento_exigem_resultado_com_explicacao() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "acompanhado da explicação" in template, fase
        assert "nunca o resultado isolado" in template, fase
        assert "fórmulas usadas" in template and "convenções adotadas" in template, fase
        assert "inclua um critério de aceite que a verifique" in template, fase
