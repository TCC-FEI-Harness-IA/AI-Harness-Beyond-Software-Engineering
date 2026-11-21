"""Captura, do caso de uso real, os frames ao vivo e a sessão persistida de uma mesma execução.

Usada para gerar as fixtures de paridade do frontend (`apps/frontend/src/test/fixtures/capture-*.json`):
cada fixture traz os frames exatamente como o WebSocket os enviaria (`ThinkingEvent` convertido pela mesma
função do composition root e serializado com `model_dump`) e o documento da sessão gravado pelo
`SessionDocumentMapper` ao fim da execução. O modelo é roteirizado; nenhuma chamada paga é feita.

Para regravar as fixtures depois de mudar a emissão de eventos:

    PYTHONPATH=. .venv/bin/python -m tests.doubles.frontend_parity_capture ../frontend/src/test/fixtures
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    criterios,
    global_aprovado,
    plano_aprovado,
    aprendizados,
    plano_reprovado,
    problema_do_plano,
    relatorio,
    reprovado_tecnico,
    resolucao,
    resposta_final,
    tarefa_aprovada,
)

FIXTURE_PREFIX = "capture-"


def _tarefa(task_id: str, title: str, criteria: tuple[str, ...], **extra: object) -> dict[str, object]:
    return {
        "id": task_id,
        "title": title,
        "description": f"Descrição de {title.lower()}.",
        "acceptance_criteria": [{"id": f"{task_id}-AC{i}", "description": text} for i, text in enumerate(criteria, 1)],
        **extra,
    }


_ANTECIPADA = json.dumps({"tasks": [
    _tarefa("T1", "Mostrar que o 4 é a resposta", ("Provar que 4 atende às três condições.",)),
]})
_APROVADO = json.dumps({"tasks": [
    _tarefa("T1", "Testar as condições em cada número", (
        "Determinar e justificar quais números são primos, pares e maiores que 2.",
        "Explicar o teste de cada condição em 2, 4 e 6.",
    )),
    _tarefa("T2", "Escolher a alternativa sustentada", ("Escolher a alternativa sustentada pela análise de T1.",),
            depends_on=["T1"]),
]})
_REPROVACAO = plano_reprovado(problema_do_plano(
    task_id="T1", criterion_id="T1-AC1",
    problem="The criterion requires a conclusion that execution has not established.",
    adjustment="Ask the task to determine which numbers meet the conditions, keeping the result open.",
))
_EXECUCAO = [
    resolucao("Nenhum número atende às três condições."),
    relatorio(("T1-AC1", True), ("T1-AC2", True), ("T1-TECH", True)),
    aprendizados("Nenhum de 2, 4 e 6 é primo, par e maior que 2."),
    *tarefa_aprovada("T2", "D) NDA.", "A alternativa sustentada é D."),
    global_aprovado(),
]

# Cada caso: roteiro do modelo e limite de planejamento do guardião programável.
CASES: dict[str, tuple[list[str], int]] = {
    # Revisão do plano, auditoria de A.3 e auditoria de C.3 seguida da resposta aceita.
    "v2-plan-revision-c3-audit": ([
        criterios(), _ANTECIPADA, '{"approved": "false"}', _REPROVACAO, _APROVADO, plano_aprovado(),
        anotacoes_do_enunciado("Alternativas: A) 2 B) 4 C) 6 D) NDA"), *_EXECUCAO,
        "resposta sem json", resposta_final("D) Nenhuma das anteriores"),
    ], 5),
    # Planejamento esgotado antes de A.4: nenhuma tarefa nem resposta.
    "v2-planning-exhausted": ([criterios(), _ANTECIPADA, _REPROVACAO, _ANTECIPADA, _REPROVACAO], 2),
    # Nova fase de validação — 02: B.2 reprova a primeira resolução só pelo critério técnico `T1-TECH`;
    # B.1 é retentada com o feedback e aprovada. O `execute` mostra só os critérios planejados.
    "v2-tech-retry": ([
        criterios(), json.dumps({"tasks": [_tarefa("T1", "Testar as condições em cada número", (
            "Explicar o teste de cada condição em 2, 4 e 6.",))]}), plano_aprovado(), anotacoes_do_enunciado(),
        resolucao("Como 2 é par e primo, a alternativa A atende."),
        reprovado_tecnico("T1", "A condição 'maior que 2' foi ignorada: 2 não é maior que 2. Refaça o teste de 2."),
        resolucao("Nenhum número atende às três condições: 2 não é maior que 2; 4 e 6 não são primos."),
        relatorio(("T1-AC1", True), ("T1-TECH", True)),
        aprendizados("Nenhum de 2, 4 e 6 é primo, par e maior que 2."),
        global_aprovado(), resposta_final("D) Nenhuma das anteriores"),
    ], 5),
    # C.3 esgota as correções: as saídas recusadas ficam auditadas e não há resposta final.
    "v2-c3-exhausted": ([
        criterios(), _APROVADO, plano_aprovado(), anotacoes_do_enunciado(), *_EXECUCAO,
        "recusada 1", "recusada 2", "recusada 3",
    ], 5),
}


def _to_frame(event: Any) -> dict[str, Any]:
    """Converte o evento com a mesma função do composition root e serializa como o router (`model_dump`)."""
    startup = RalphThinkingStartup.__new__(RalphThinkingStartup)
    return startup._RalphThinkingStartup__to_event_dto(event=event).model_dump()


async def capture(name: str) -> dict[str, Any]:
    """Executa o caso e devolve os frames capturados e a sessão persistida da mesma execução.

    Args:
        name: Chave de `CASES`.

    Returns:
        dict[str, Any]: `{"events": [...], "session": {...}}`.
    """
    responses, planning_attempts = CASES[name]
    scenario = RalphScenario(responses=responses, cost_guard=FakeCostGuard(max_planning_attempts=planning_attempts))
    frames: list[dict[str, Any]] = []
    try:
        async for event in scenario.stream():
            frames.append(_to_frame(event))
    except Exception:  # noqa: BLE001 - a falha encerra a execução depois do frame de erro, já capturado.
        pass
    return {"events": frames, "session": SessionDocumentMapper().to_document(session=scenario.session)}


def serialize(document: dict[str, Any]) -> str:
    """Serialização estável das fixtures."""
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


async def _write_all(directory: Path) -> None:
    for name in CASES:
        (directory / f"{FIXTURE_PREFIX}{name}.json").write_text(serialize(await capture(name)), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_write_all(Path(sys.argv[1])))
