import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider

_PLACEHOLDERS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: {"user_question"},
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"user_question", "max_tasks"},
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: {"user_question"},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {
        "task_description", "task_acceptance_criteria", "learnings", "previous_attempts"
    },
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: {"preliminary_result", "task_acceptance_criteria", "learnings"},
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: {"task_description", "approved_result", "task_history", "learnings"},
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


def test_template_a2_orienta_decomposicao_parcimoniosa_e_por_condicoes() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION).lower().split())

    assert "menor número possível de tarefas" in template
    assert "nunca por alternativa" in template
    assert "evite tarefas burocráticas ou redundantes" in template


def test_template_b4_proibe_metadados_da_tarefa_e_do_validador_nos_aprendizados() -> None:
    template = " ".join(_provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).lower().split())

    assert "conteúdo do problema" in template
    assert "menções à própria tarefa" in template
    assert "veredito de aprovação" in template
    assert "dados de controle, metadados operacionais" not in template


# ── B.4 — Resultados parciais da tarefa aprovada ────────────────────────────


def _b4() -> str:
    return " ".join(_provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION).split())


def test_template_b4_recebe_o_material_da_extracao_em_areas_delimitadas_e_nao_da_conversa() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION)

    assert "<resultado_aprovado>\n{{approved_result}}\n</resultado_aprovado>" in template
    assert "<historico_da_tarefa>\n{{task_history}}\n</historico_da_tarefa>" in template
    assert "janela de contexto própria" in _b4()
    assert "contexto acima" not in _b4()
    # O histórico é material da extração: as áreas da tarefa vêm antes das instruções.
    assert template.index("{{task_history}}") < template.index("## Instruções")


def test_template_b4_exige_registrar_todo_resultado_parcial_novo_com_significado_autonomo() -> None:
    template = _b4().lower()

    assert "registre todo resultado parcial novo do resultado aprovado" in template
    assert "sem o histórico anterior" in template
    assert "a simplicidade de uma conclusão não justifica omiti-la" in template
    assert "percorra o resultado aprovado conclusão por conclusão" in template


def test_template_b4_define_o_que_preservar_para_valores_classificacoes_e_relacoes() -> None:
    template = _b4().lower()

    assert "**valores:** preserve a grandeza" in template
    assert "o valor, a unidade de medida e as condições relevantes" in template
    assert "**classificações:** identifique a afirmação" in template
    assert "sua classificação" in template and "um motivo breve" in template
    assert "**relações:** preserve a fórmula ou relação e as hipóteses necessárias" in template


def test_template_b4_distingue_o_fato_compacto_da_breve_explicacao_sem_copiar_a_resolucao() -> None:
    template = _b4()

    assert "**fato compacto**" in template and "**breve explicação**" in template
    assert "Não copie a resolução completa" in template
    assert '"A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade."' in template


def test_template_b4_prioriza_a_conclusao_aprovada_e_descarta_valores_refutados() -> None:
    template = _b4().lower()

    assert "priorize a conclusão finalmente aprovada" in template
    assert "refutados, corrigidos ou substituídos" in template
    assert "não são aprendizados vigentes" in template


def test_template_b4_proibe_instrucoes_criterios_vereditos_relatos_e_duplicatas() -> None:
    template = _b4().lower()

    assert "instruções da tarefa" in template
    assert "critérios de aceite" in template
    assert "vereditos" in template
    assert "relatos do processo" in template
    assert "fatos que já constam em **aprendizados pontuais**, mesmo com outras palavras" in template


def test_template_b4_so_admite_lista_vazia_sem_fato_novo() -> None:
    template = _b4()

    assert '`{"learnings": []}` **somente**' in template
    assert "nenhum fato novo" in template
    assert "todas as suas conclusões já constarem em **Aprendizados Pontuais**" in template


def test_templates_orientam_avaliacao_relativa_por_eliminacao_sem_hiper_literalismo() -> None:
    provider = _provider()

    a1 = " ".join(provider.get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA).lower().split())
    assert "melhor ajuste por eliminação" in a1
    assert "aprová-los ou descartá-los de antemão" in a1

    for fase in (
        ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
        ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
    ):
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "eliminação" in template, fase
        assert "100% literal" in template or "hiper-litera" in template, fase


def test_templates_de_planejamento_proibem_pre_calculo_e_pedem_escopo_afirmativo() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "pré-calcular" in template, fase
        assert "afirmativa e delimitadora" in template, fase
        assert "restringe-se exclusivamente a" in template, fase


def test_templates_de_planejamento_exigem_que_a_ultima_tarefa_conclua_a_grandeza_final() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        template = " ".join(provider.get(phase=fase).lower().split())
        assert "última tarefa" in template, fase
        assert "grandeza" in template, fase


def test_templates_de_verificacao_pedem_decision_por_ultimo_no_json() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        formato = provider.get(phase=fase).split("## Formato de saída", 1)[1]
        assert formato.index('"criteria_evaluation"') < formato.index('"unmet_criteria_ids"') < formato.index(
            '"decision"'
        ), fase




    assert "## Tentativas anteriores desta tarefa" in template
    assert "<tentativas_anteriores>" in template
    assert template.index("{{previous_attempts}}") < template.index("## Formato de saída")


def test_template_b4_extrai_do_historico_delimitado_e_nao_do_contexto_acima() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION)
    normalizado = " ".join(template.lower().split())

    assert "## Histórico da tarefa" in template
    assert "<historico_da_tarefa>" in template
    assert "contexto acima" not in normalizado
    assert "não continue" in normalizado
    assert template.index("{{task_history}}") < template.index("## Formato de saída")
