import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from src.infra.startups.ralph_loop_startup import RalphLoopStartup

question = (
    "Em uma cidade, 70% dos habitantes falam inglês, 60% falam francês e 50% falam alemão. "
    "Todos os habitantes falam pelo menos um desses três idiomas e 30% falam os três idiomas simultaneamente. "
    "Qual é a porcentagem exata de habitantes que falam exatamente dois desses idiomas?\n"
    "A) 20%\n"
    "B) 30%\n"
    "C) 40%\n"
    "D) 50%"
)


async def main() -> None:
    reconfig = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfig):
        reconfig(encoding="utf-8")

    print("Iniciando execução do Ralph Loop via Azure AI Foundry (Llama-3.3-70B-Instruct)...\n")
    startup = RalphLoopStartup()

    # Executa com 1 rodada de planejamento adicional e até 2 retentativas por tarefa
    summary = await startup.ralph_loop_use_case.execute_sync(
        user_input=question,
        provider="azure_foundry",
        model_name="Llama-3.3-70B-Instruct",
        max_tokens=1024,
        temperature=0.2,
        max_retries_per_task=2,
        max_additional_planning_rounds=1,
    )

    print("\n" + "=" * 60)
    print("RELATÓRIO DA EXECUÇÃO DO RALPH LOOP COM AZURE FOUNDRY")
    print("=" * 60)
    print(f"\n[PERGUNTA]:\n{summary.question}\n")

    print("[FASE A.1 — CRITÉRIOS DE ACEITE GERAIS]:")
    for crit in summary.general_criteria:
        print(f"  - {crit}")

    print(f"\n[FASE B — TAREFAS EXECUTADAS E HOMOLOGADAS (TOTAL: {summary.tasks_count})]:")
    for tid, res in summary.approved_results.items():
        print(f"\n--- {tid} ---")
        print(res.strip())

    print("\n[FASE B.4 — APRENDIZADOS FACTUAIS ACUMULADOS (FRESH CONTEXT)]:")
    for learn in summary.accumulated_learnings:
        print(f"  * {learn}")

    print("\n" + "=" * 60)
    print(f"[FASE C.3 — RESPOSTA FINAL AO USUÁRIO]:\n>> {summary.final_answer}")
    print(f"[CONSUMO TOTAL DE TOKENS]: {summary.total_tokens}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
