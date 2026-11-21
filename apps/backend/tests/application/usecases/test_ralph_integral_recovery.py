"""Integração com rede falsa: o plano aceito segue sozinho e a próxima fase abre outra janela."""
import json
import logging

import pytest

from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import plano_aprovado
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado, global_aprovado, resposta_final, tarefa, tarefa_aprovada,
)


@pytest.mark.parametrize("pergunta", ["Determine the requested quantity.", "Choose the quantity: A) 2 B) 3."])
async def test_so_o_plano_corrigido_e_encaminhado_e_a_recuperacao_nao_atravessa_fases(pergunta: str) -> None:
    plano = {"tasks": [tarefa(task_id) for task_id in ("T1", "T2", "T3")]}
    plano["tasks"][0]["description"] = "Record all relevant observations with their conditions. " * 40
    plano["tasks"][2]["description"] = "Determine the requested quantity using the established relations."
    corrigida = json.dumps(plano)
    del plano["tasks"][2]["title"]
    recusada = json.dumps(plano)
    assert recusada.index('"id": "T2"') > 1000
    criterios = json.dumps({"general_acceptance_criteria": [
        {"id": "AC1", "description": "Answer the requested question."},
        {"id": "AC2", "description": "Use the requested language and presentation."},
    ]})
    provider = FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))
    cenario = RalphScenario(
        responses=[
            criterios, recusada, corrigida, plano_aprovado(), anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "observation"),
            *tarefa_aprovada("T2", "relation"),
            *tarefa_aprovada("T3", "quantity"),
            global_aprovado(), resposta_final("quantity"),
        ],
        template_provider=provider,
    )

    eventos = await cenario.run(question=pergunta)

    assert eventos[-1].content == "quantity"
    sessao = cenario.session
    assert sessao.status is SessionStatusEnum.COMPLETED
    mensagens_a2 = [m for m in sessao.messages if m.phase is ThinkingPhaseEnum.A2_TASK_DECOMPOSITION]
    auditoria, aceita = mensagens_a2
    assert recusada in auditoria.content
    for task in json.loads(corrigida)["tasks"]:
        assert task["title"] in aceita.content
        assert task["description"] in aceita.content
    assert [m.text for m in aceita.prompt_input] == cenario.llm.texts_of(2)
    assert aceita.prompt_input[1].text == recusada
    assert tuple(cenario.llm.conversations[1]) == auditoria.prompt_input
    assert [i.content_accepted for i in sessao.invocations[1:3]] == [False, True]
    assert sessao.invocations[2].recovers_invocation_id == sessao.invocations[1].id
    assert sessao.invocations[1].context_id == sessao.invocations[2].context_id
    assert sessao.invocations[3].context_id != sessao.invocations[2].context_id
    assert sessao.invocations[3].recovers_invocation_id is None
    assert [i.temperature for i in sessao.invocations[:4]] == [0.3, 0.3, 1.0, 0.3]
    assert all(len(c) == 1 for i, c in enumerate(cenario.llm.conversations) if i != 2)
    assert recusada not in cenario.llm.texts_of(3)
    assert aceita.prompt_input[-1].text not in cenario.llm.texts_of(3)
    resolucoes = [m for m in sessao.messages if m.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
                  and m.source is MessageSourceEnum.LLM_AGENT]
    assert [m.task_id for m in resolucoes] == ["T1", "T2", "T3"]
    assert plano["tasks"][2]["description"] in resolucoes[-1].prompt_input[0].text
    assert sessao.totals.total_llm_calls == cenario.llm.call_count == 16
    assert sessao.totals.total_tokens == 16 * (10 + 5)
