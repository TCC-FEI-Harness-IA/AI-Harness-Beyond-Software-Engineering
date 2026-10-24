"""CLI do benchmark: python 'teste benchmark/executar.py'."""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from benchmark import DEFAULT_CONCURRENCY, MODEL, load_questions, run_benchmark, write_json, write_reports

MODULE = Path(__file__).resolve().parent
PROJECT = MODULE.parent


def arguments() -> argparse.Namespace:
    """Lê parâmetros; os defaults executam todas as questões com cinco workers."""
    parser = argparse.ArgumentParser(description="Compara inferência simples e RALPH LOOP nas questões locais.")
    parser.add_argument("--questions-dir", type=Path, default=MODULE / "QUESTOES_BENCHMARK")
    parser.add_argument("--output-dir", type=Path, default=MODULE / "resultados")
    parser.add_argument("--env-file", type=Path, default=PROJECT / "apps/backend/.env")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--dry-run", action="store_true", help="Valida o dataset sem chamar modelos nem criar relatórios.",
    )
    args = parser.parse_args()
    if args.concurrency < 1 or args.max_tokens < 1 or not 0 <= args.temperature <= 1:
        parser.error("Concorrência e max-tokens devem ser positivos; temperatura deve estar entre 0 e 1.")
    return args


def main() -> int:
    """Executa uma rodada e grava relatórios em uma pasta exclusiva."""
    args = arguments()
    questions = load_questions(args.questions_dir.resolve())
    print(f"{len(questions)} questões; modelo: {MODEL}; concorrência: {args.concurrency}.", flush=True)
    if args.dry_run:
        for question in questions:
            print(f"  {question.id}: simples → RALPH LOOP")
        return 0

    from backend import BackendFlows, configure_backend

    now = datetime.now(timezone.utc)
    output = args.output_dir.resolve() / f"{now:%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"
    configure_backend(PROJECT, output, args.env_file.resolve())
    output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "model": MODEL, "provider": "open_router", "concurrency": args.concurrency,
        "max_tokens": args.max_tokens, "temperature": args.temperature,
        "started_at": now.isoformat(), "questions_dir": str(args.questions_dir.resolve()),
        "question_ids": [question.id for question in questions],
    }
    write_json(output / "execucao.json", metadata)
    instruction = (MODULE / "prompt.md").read_text(encoding="utf-8")
    (output / "prompt.md").write_text(instruction, encoding="utf-8")
    started = perf_counter()
    flows = BackendFlows(output, args.max_tokens, args.temperature)
    results = asyncio.run(run_benchmark(questions, flows, instruction, args.concurrency, output))
    metadata.update(finished_at=datetime.now(timezone.utc).isoformat(), seconds=round(perf_counter() - started, 3))
    write_reports(output, results, metadata)
    print(f"\nRelatório: {output / 'relatorio.md'}", flush=True)
    for flow, label in (("simple", "Simples"), ("ralph", "RALPH LOOP")):
        correct = sum(getattr(result, flow).correct for result in results)
        print(f"{label}: {correct} acertos × {len(results) - correct} erros")
    return int(any(getattr(result, flow).error for result in results for flow in ("simple", "ralph")))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        print("\nInterrompido. Checkpoints das questões e sessões ficam na pasta da execução.", file=sys.stderr)
        raise SystemExit(130)
