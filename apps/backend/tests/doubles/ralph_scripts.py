"""Roteiros de respostas do modelo, reaproveitados pelos testes do fluxo Ralph.

Cada função devolve a saída bruta (JSON) que o modelo produziria numa etapa. Os critérios
gerais do roteiro são `AC1` e `AC2`; o critério planejado de cada tarefa é `<tarefa>-AC1`. Desde a
nova fase de validação — 02, o conjunto efetivo de B.2 de uma tarefa comum é `<tarefa>-AC1` mais o
critério técnico fixo `<tarefa>-TECH`: os relatórios locais abaixo avaliam os dois, cada um com o seu
veredito, para que nenhum cenário de execução nova deixe de avaliar a validade técnica.
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


def resolucao(texto: str, conclusao: str | None = None) -> str:
    """Saída de B.1. Sem conclusão informada, a própria resolução faz as vezes de conclusão."""
    return json.dumps({"task_id": "T1", "result": texto, "conclusion": texto if conclusao is None else conclusao})


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


def tech(task_id: str = "T1") -> str:
    """Identificador do critério técnico fixo que o harness acrescenta à tarefa."""
    return f"{task_id}-TECH"


def aprovado(task_id: str = "T1") -> str:
    """Verificação local aprovada: o critério planejado e o técnico foram atendidos."""
    return relatorio((f"{task_id}-AC1", True), (tech(task_id), True))


def reprovado(task_id: str = "T1") -> str:
    """Verificação local reprovada pelo critério planejado; a validade técnica foi atendida."""
    return relatorio((f"{task_id}-AC1", False), (tech(task_id), True))


def reprovado_tecnico(task_id: str = "T1", justificativa: str = "A premissa decisiva nao foi fornecida.") -> str:
    """Verificação local reprovada só pelo critério técnico: o planejado foi atendido."""
    return json.dumps(
        {
            "criteria_evaluation": [
                {"criterion_id": f"{task_id}-AC1", "met": True, "justification": "As etapas pedidas estao presentes."},
                {"criterion_id": tech(task_id), "met": False, "justification": justificativa},
            ],
            "unmet_criteria_ids": [tech(task_id)],
            "decision": "reproved",
        }
    )


def global_aprovado() -> str:
    """Verificação global aprovada: avalia os dois critérios gerais."""
    return relatorio(("AC1", True), ("AC2", True))


def global_reprovado(*pendentes: str) -> str:
    """Verificação global reprovada: avalia os dois critérios gerais, com as pendências dadas."""
    return relatorio(*[(criterion_id, criterion_id not in pendentes) for criterion_id in ("AC1", "AC2")])


def plano_aprovado() -> str:
    """Saída de A.3 (fluxo versão 2): o plano candidato foi aprovado, sem problemas pendentes."""
    return json.dumps({"approved": True, "issues": []})


def problema_do_plano(
    task_id: str | None = "T1",
    criterion_id: str | None = None,
    problem: str = "O critério antecipa uma conclusão ainda não estabelecida.",
    adjustment: str = "Pedir a investigação mantendo a conclusão em aberto.",
) -> dict[str, object]:
    """Um problema do relatório de A.3; referências nulas indicam o plano inteiro ou a tarefa inteira."""
    return {"task_id": task_id, "criterion_id": criterion_id, "problem": problem, "adjustment": adjustment}


def plano_reprovado(*problemas: dict[str, object]) -> str:
    """Saída de A.3 reprovando o candidato; sem problemas informados, aponta a tarefa T1 inteira."""
    return json.dumps({"approved": False, "issues": list(problemas) or [problema_do_plano()]})


def aprendizados(*fatos: str) -> str:
    return json.dumps({"learnings": list(fatos)})


def anotacoes_do_enunciado(*fatos: str) -> str:
    """Saída de A.4 (A.3 no fluxo versão 1): os pontos de atenção do enunciado. Sem fatos, nada a anotar."""
    return aprendizados(*fatos)


def resposta_final(texto: str = "D) Nenhuma das anteriores") -> str:
    return json.dumps({"final_answer": texto})


def tarefa_aprovada(task_id: str, resultado: str, *fatos: str) -> list[str]:
    return [resolucao(resultado), aprovado(task_id), aprendizados(*fatos)]


def roteiro_feliz(*anotacoes: str) -> list[str]:
    return [
        criterios(),
        tarefas("T1", "T2", "T3"),
        plano_aprovado(),
        anotacoes_do_enunciado(*anotacoes),
        *tarefa_aprovada("T1", "2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        *tarefa_aprovada("T2", "2, 4 e 6 sao pares", "Todo numero par e divisivel por 2."),
        *tarefa_aprovada("T3", "apenas 4 e 6 sao maiores que 2", "O unico primo par e o 2."),
        global_aprovado(),
        resposta_final(),
    ]
