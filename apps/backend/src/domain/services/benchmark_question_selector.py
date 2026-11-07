import random
from collections import defaultdict, deque

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError


def select_subject_questions(
    questions: list[BenchmarkQuestion], subjects: tuple[str, ...], count: int | None, seed: int,
) -> list[BenchmarkQuestion]:
    """Amostra por rodadas entre disciplinas, embaralhadas com uma semente local."""
    available = {question.subject for question in questions}
    unknown = set(subjects) - available
    if unknown:
        raise InvalidBenchmarkRequestError(f"Disciplinas desconhecidas: {', '.join(sorted(unknown))}.")
    if not 0 <= seed <= 2**32 - 1:
        raise InvalidBenchmarkRequestError("sample_seed deve estar entre 0 e 4294967295.")
    grouped: dict[str, list[BenchmarkQuestion]] = defaultdict(list)
    for question in questions:
        if not subjects or question.subject in subjects:
            grouped[question.subject].append(question)
    rng = random.Random(seed)
    queues = []
    for subject in sorted(grouped):
        bucket = sorted(grouped[subject], key=lambda question: question.id)
        rng.shuffle(bucket)
        queues.append(deque(bucket))
    rng.shuffle(queues)
    selected = []
    while queues:
        remaining = []
        for queue in queues:
            selected.append(queue.popleft())
            if queue:
                remaining.append(queue)
        queues = remaining
    if count is not None and not 1 <= count <= len(selected):
        raise InvalidBenchmarkRequestError(f"question_count deve estar entre 1 e {len(selected)}. Valor: {count}.")
    return selected if count is None else selected[:count]


# Compatibilidade com consumidores do seletor original do MMLU.
select_mmlu_questions = select_subject_questions
