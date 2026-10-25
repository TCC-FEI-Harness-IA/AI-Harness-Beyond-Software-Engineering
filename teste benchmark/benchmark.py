"""Carga, execução concorrente e avaliação determinística das questões."""

import asyncio
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Protocol

MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_CONCURRENCY = 5
OPTION = re.compile(r"^([A-E])\)\s+(.+)$", re.MULTILINE)
FINAL = re.compile(r"^RESPOSTA_FINAL:\s*([A-E])\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Question:
    """Enunciado e gabarito local, que nunca é incluído no prompt."""

    id: str
    statement: str
    options: dict[str, str]
    expected: str


@dataclass(frozen=True)
class Reply:
    """Resposta de um fluxo e identificação da sessão persistida."""

    response: str = ""
    session_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class Outcome:
    """Avaliação da resposta; falhas também contam como não acertos."""

    response: str
    selected: str | None
    correct: bool
    error: str | None
    session_id: str | None
    seconds: float


@dataclass
class Result:
    """Resultado de uma questão nos dois fluxos, inclusive execução parcial."""

    question_id: str
    expected: str
    simple: Outcome | None = None
    ralph: Outcome | None = None


class Flows(Protocol):
    """Porta para os fluxos reais do backend ou duplos de teste."""

    async def simple(self, question_id: str, prompt: str) -> Reply: ...

    async def ralph(self, question_id: str, prompt: str) -> Reply: ...


def load_questions(directory: Path) -> list[Question]:
    """Carrega e valida todos os pares de arquivos antes de chamar um modelo."""
    if not directory.is_dir():
        raise ValueError(f"Diretório de questões não encontrado: {directory}")
    questions = []
    for folder in sorted(path for path in directory.iterdir() if path.is_dir()):
        try:
            statement = (folder / "enunciado.md").read_text(encoding="utf-8").strip()
            answer = (folder / "alternativa_correta.md").read_text(encoding="utf-8").strip()
        except OSError as error:
            raise ValueError(f"Questão incompleta em {folder.name}: {error}") from error
        options = OPTION.findall(statement)
        expected = OPTION.fullmatch(answer)
        if [letter for letter, _ in options] != list("ABCDE") or expected is None:
            raise ValueError(f"Alternativas ou gabarito inválidos: {folder.name}")
        mapping = dict(options)
        if mapping[expected[1]] != expected[2]:
            raise ValueError(f"Texto do gabarito difere da alternativa: {folder.name}")
        questions.append(Question(folder.name, statement, mapping, expected[1]))
    if not questions:
        raise ValueError("Nenhuma questão encontrada.")
    return questions


def selected_answer(response: str, options: dict[str, str]) -> str | None:
    """Lê o marcador final sem confundir alternativas citadas na resolução.

    Aceita também uma letra isolada ou uma alternativa completa isolada.
    Marcadores inválidos, conflitantes ou fora da última linha são recusados.
    """
    clean = response.replace("**", "").strip()
    if "RESPOSTA_FINAL:" in clean:
        matches = FINAL.findall(clean)
        if len(matches) == 1 and clean.splitlines()[-1].strip() == f"RESPOSTA_FINAL: {matches[0]}":
            return matches[0]
        return None
    if clean in options:
        return clean
    for letter, text in options.items():
        if clean == f"{letter}) {text}":
            return letter
    return None


async def evaluate(flows: Flows, name: str, question: Question, prompt: str) -> Outcome:
    """Executa um fluxo sem impedir o outro fluxo em caso de falha."""
    started = perf_counter()
    try:
        reply = await getattr(flows, name)(question.id, prompt)
    except Exception as error:
        reply = Reply(error=f"{type(error).__name__}: {error}")
    selected = selected_answer(reply.response, question.options) if reply.error is None else None
    error = reply.error
    if error is None and selected is None:
        error = "Resposta sem alternativa final válida e inequívoca."
    outcome = Outcome(
        response=reply.response,
        selected=selected,
        correct=error is None and selected == question.expected,
        error=error,
        session_id=reply.session_id,
        seconds=round(perf_counter() - started, 3),
    )

    persist = getattr(flows, "record_outcome", None)
    if persist is not None:
        try:
            await persist(question.id, name, outcome)
        except Exception as failure:
            outcome = replace(outcome, correct=False, error=f"Falha ao persistir avaliação: {failure}")
    return outcome


def write_json(path: Path, payload: object) -> None:
    """Grava atomicamente um JSON, preservando o último checkpoint completo."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def run_benchmark(
    questions: list[Question],
    flows: Flows,
    instruction: str,
    concurrency: int = DEFAULT_CONCURRENCY,
    output: Path | None = None,
) -> list[Result]:
    """Distribui questões por uma fila FIFO; cada worker faz simples → Ralph."""
    if concurrency < 1:
        raise ValueError("A concorrência deve ser maior que zero.")
    queue: asyncio.Queue[Question | None] = asyncio.Queue()
    results: dict[str, Result] = {}
    workers = min(concurrency, len(questions))
    for question in questions:
        queue.put_nowait(question)
    for _ in range(workers):
        queue.put_nowait(None)

    async def worker() -> None:
        while True:
            question = await queue.get()
            try:
                if question is None:
                    return
                result = Result(question.id, question.expected)
                results[question.id] = result
                prompt = f"{question.statement}\n\n{instruction.strip()}"
                for name in ("simple", "ralph"):
                    print(f"[{question.id}] Iniciando {name}", flush=True)
                    outcome = await evaluate(flows, name, question, prompt)
                    setattr(result, name, outcome)
                    if output is not None:
                        await asyncio.to_thread(write_json, output / f"{question.id}.json", asdict(result))
                    status = "CERTO" if outcome.correct else "ERRADO"
                    detail = f"; falha: {outcome.error}" if outcome.error else ""
                    print(f"[{question.id}] {name}: {status}{detail}", flush=True)
            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as group:
        for _ in range(workers):
            group.create_task(worker())
    await queue.join()
    return [results[question.id] for question in questions]


def totals(results: list[Result], flow: str) -> dict[str, int]:
    """Conta acertos, erros e o subconjunto de erros causado por falhas."""
    outcomes = [getattr(result, flow) for result in results]
    correct = sum(outcome is not None and outcome.correct for outcome in outcomes)
    return {
        "acertos": correct,
        "erros": len(results) - correct,
        "falhas": sum(outcome is not None and outcome.error is not None for outcome in outcomes),
        "nao_executadas": sum(outcome is None for outcome in outcomes),
    }


def write_reports(output: Path, results: list[Result], metadata: dict[str, object]) -> None:
    """Gera resultados detalhados JSON e um relatório breve em Markdown."""
    summary = {flow: totals(results, flow) for flow in ("simple", "ralph")}
    write_json(output / "resultados.json", {
        "execucao": metadata, "totais": summary, "questoes": [asdict(result) for result in results],
    })
    lines = [
        "# Relatório do benchmark", "",
        f"Modelo em todas as chamadas: `{metadata['model']}`.", "",
        f"Concorrência: {metadata['concurrency']} questões; ordem por questão: simples → RALPH LOOP.", "",
        "| Questão | Gabarito | Simples | RALPH LOOP |", "| --- | --- | --- | --- |",
    ]
    for result in results:
        cells = []
        for outcome in (result.simple, result.ralph):
            if outcome is None:
                cells.append("NÃO EXECUTADA")
            else:
                status = "CERTO" if outcome.correct else "ERRADO"
                detail = "; falha" if outcome.error else ""
                cells.append(f"{status} ({outcome.selected or 'sem alternativa'}{detail})")
        lines.append(f"| {result.question_id} | {result.expected} | {cells[0]} | {cells[1]} |")
    lines += ["", "| Fluxo | Acertos | Erros | Acurácia | Falhas incluídas nos erros |",
              "| --- | --- | --- | --- | --- |"]
    for name, label in (("simple", "Inferência simples"), ("ralph", "RALPH LOOP adaptado")):
        values = summary[name]
        accuracy = 100 * values['acertos'] / len(results) if results else 0
        lines.append(
            f"| {label} | {values['acertos']} | {values['erros']} | {accuracy:.1f}% | {values['falhas']} |"
        )
    lines += ["", "Falhas técnicas e respostas sem alternativa válida contam como erros de acurácia.",
              "Os JSONs guardam respostas brutas, erros, tempos e IDs das sessões.", ""]
    (output / "relatorio.md").write_text("\n".join(lines), encoding="utf-8")
