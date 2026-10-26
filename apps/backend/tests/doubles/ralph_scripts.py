"""Roteiros de respostas do modelo, reaproveitados pelos testes do fluxo Ralph.

Cada função devolve a saída bruta (JSON) que o modelo produziria numa etapa. Os critérios
gerais do roteiro são `AC1` e `AC2`; os critérios de cada tarefa são `<tarefa>-AC1`.
"""
import json


def criterios() -> str:
    return json.dumps(
        {
            "general_acceptance_criteria": [
                {"id": "AC1", "description": "responder em portugues"},
                {"id": "AC2", "description": "selecionar uma das alternativas"},
            ]
        }
    )


def tarefa(task_id: str) -> dict[str, object]:
    return {
        "id": task_id,
        "title": f"titulo de {task_id}",
        "description": f"descricao de {task_id}",
        "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": f"criterio de {task_id}"}],
    }


def tarefas(*ids: str) -> str:
    return json.dumps({"tasks": [tarefa(task_id) for task_id in ids]})


def resolucao(texto: str) -> str:
    return json.dumps({"task_id": "T1", "result": texto})


def relatorio(*avaliacoes: tuple[str, bool]) -> str:
    falhas = [criterion_id for criterion_id, met in avaliacoes if not met]
    return json.dumps(
        {
            "decision": "reproved" if falhas else "approved",
            "criteria_evaluation": [
                {"criterion_id": criterion_id, "met": met, "justification": "atende" if met else "nao atende"}
                for criterion_id, met in avaliacoes
            ],
            "unmet_criteria_ids": falhas,
        }
    )


def aprovado(task_id: str = "T1") -> str:
    """Verificação local aprovada: avalia o único critério da tarefa."""
    return relatorio((f"{task_id}-AC1", True))


def reprovado(task_id: str = "T1") -> str:
    """Verificação local reprovada: o único critério da tarefa não foi atendido."""
    return relatorio((f"{task_id}-AC1", False))


def global_aprovado() -> str:
    """Verificação global aprovada: avalia os dois critérios gerais."""
    return relatorio(("AC1", True), ("AC2", True))


def global_reprovado(*pendentes: str) -> str:
    """Verificação global reprovada: avalia os dois critérios gerais, com as pendências dadas."""
    return relatorio(*[(criterion_id, criterion_id not in pendentes) for criterion_id in ("AC1", "AC2")])


def aprendizados(*fatos: str) -> str:
    return json.dumps({"learnings": list(fatos)})


def anotacoes_do_enunciado(*fatos: str) -> str:
    """Saída de A.3: os pontos de atenção do enunciado. Sem fatos, o enunciado não tinha nada a anotar."""
    return aprendizados(*fatos)


def resposta_final(texto: str = "D) Nenhuma das anteriores") -> str:
    return json.dumps({"final_answer": texto})


def tarefa_aprovada(task_id: str, resultado: str, *fatos: str) -> list[str]:
    return [resolucao(resultado), aprovado(task_id), aprendizados(*fatos)]


def roteiro_feliz(*anotacoes: str) -> list[str]:
    return [
        criterios(),
        tarefas("T1", "T2", "T3"),
        anotacoes_do_enunciado(*anotacoes),
        *tarefa_aprovada("T1", "2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        *tarefa_aprovada("T2", "2, 4 e 6 sao pares", "Todo numero par e divisivel por 2."),
        *tarefa_aprovada("T3", "apenas 4 e 6 sao maiores que 2", "O unico primo par e o 2."),
        global_aprovado(),
        resposta_final(),
    ]
