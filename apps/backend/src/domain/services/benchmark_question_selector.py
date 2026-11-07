import random
from collections import Counter, defaultdict, deque

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


def select_vestibular_questions(
    questions: list[BenchmarkQuestion], subject_counts: dict[str, int], count: int | None = None,
) -> list[BenchmarkQuestion]:
    """Escolhe as primeiras questões de cada matéria, mantendo a ordem do dataset.

    Matérias omitidas ou com quantidade zero ficam fora da bateria. Se o total for informado,
    ele deve coincidir com a soma das quantidades por matéria.

    Raises:
        InvalidBenchmarkRequestError: Quando uma matéria é desconhecida, uma cota é inválida,
            nenhuma questão é escolhida ou o total diverge da soma das cotas.
    """
    available = Counter(question.subject for question in questions if question.subject is not None)
    unknown = subject_counts.keys() - available.keys()
    if unknown:
        raise InvalidBenchmarkRequestError(f"Matérias desconhecidas em subject_counts: {', '.join(sorted(unknown))}.")
    for subject, requested in subject_counts.items():
        if type(requested) is not int or not 0 <= requested <= available[subject]:
            raise InvalidBenchmarkRequestError(
                f"subject_counts[{subject}] deve ser um inteiro entre 0 e {available[subject]}. Valor: {requested}."
            )
    total = sum(subject_counts.values())
    if total == 0:
        raise InvalidBenchmarkRequestError("subject_counts deve selecionar pelo menos uma questão.")
    if count is not None and count != total:
        raise InvalidBenchmarkRequestError(f"question_count deve coincidir com a soma de subject_counts ({total}).")
    remaining = dict(subject_counts)
    selected = []
    for question in questions:
        if remaining.get(question.subject, 0) > 0:
            selected.append(question)
            remaining[question.subject] -= 1
    return selected
