import csv
import hashlib
import io
import json
import random
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider

GPQA_REVISION = "56686c06f5e19865c153de0fdb11be3890014df7"
GPQA_CHOICE_SEED = 0
_DATA_PATH = Path(__file__).resolve().parents[1] / "benchmark/gpqa"
_MEMBER = "dataset/gpqa_diamond.csv"
_PASSWORD = b"deserted-untie-orchid"  # Senha pública fornecida pelos autores.
_INSTRUCTION = (
    "Solve the multiple-choice question above. Select exactly one of A, B, C, or D, preserving the original order. "
    "Reason carefully before answering. You may explain your reasoning, but end your response with a single "
    "line in this exact format: RESPOSTA_FINAL: LETTER (replace LETTER with your selected letter)."
)


class GPQABenchmarkQuestionProvider(IBenchmarkQuestionProvider):
    """GPQA Diamond local: arquivo oficial protegido, zero exemplos e permutação fixa de alternativas."""

    def __init__(self, few_shot: int = 0, data_path: Path = _DATA_PATH) -> None:
        if few_shot != 0:
            raise ValueError("GPQA Diamond aceita somente few_shot 0.")
        self.data_path = data_path
        self._questions: list[BenchmarkQuestion] | None = None

    def definition(self) -> BenchmarkDefinition:
        return BenchmarkDefinition(
            dataset=BenchmarkDatasetEnum.GPQA, revision=GPQA_REVISION,
            protocol="generative_0shot", split="diamond",
        )

    def answer_instruction(self) -> str:
        return _INSTRUCTION

    def list_questions(self) -> list[BenchmarkQuestion]:
        if self._questions is None:
            try:
                self._questions = self._load_questions()
            except (OSError, KeyError, TypeError, json.JSONDecodeError, BadZipFile, RuntimeError,
                    UnicodeError, csv.Error) as error:
                raise ValueError(f"Dataset GPQA local ausente ou inválido: {error}") from error
        return list(self._questions)

    def _load_questions(self) -> list[BenchmarkQuestion]:
        manifest = json.loads((self.data_path / "manifest.json").read_text("utf-8"))
        if manifest["revision"] != GPQA_REVISION or manifest["choice_seed"] != GPQA_CHOICE_SEED:
            raise ValueError("Revisão ou semente de alternativas GPQA incompatível.")
        archive = (self.data_path / "dataset.zip").read_bytes()
        if hashlib.sha256(archive).hexdigest() != manifest["archive_sha256"]:
            raise ValueError("Hash do arquivo GPQA difere do manifesto.")
        with ZipFile(io.BytesIO(archive)) as source:
            content = source.read(_MEMBER, pwd=_PASSWORD)
        if hashlib.sha256(content).hexdigest() != manifest["diamond_sha256"]:
            raise ValueError("Hash do CSV GPQA Diamond difere do manifesto.")
        # A permutação ocorre no corpus inteiro antes de filtros/amostras, preservando reruns e exports.
        rng = random.Random(GPQA_CHOICE_SEED)
        records = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        questions = [self._question(record, rng.sample(range(4), 4)) for record in records]
        if len(questions) != manifest["count"] or Counter(q.subject for q in questions) != manifest["subjects"]:
            raise ValueError("Contagem GPQA Diamond difere do manifesto.")
        if len({q.id for q in questions}) != len(questions):
            raise ValueError("Identificadores GPQA duplicados.")
        return sorted(questions, key=lambda question: question.id)

    @staticmethod
    def _question(record: dict, permutation: list[int]) -> BenchmarkQuestion:
        values = [record[key] for key in (
            "Question", "Record ID", "High-level domain", "Correct Answer",
            "Incorrect Answer 1", "Incorrect Answer 2", "Incorrect Answer 3",
        )]
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("Registro GPQA inválido.")
        statement, record_id, domain, *choices = values
        if domain not in ("Biology", "Chemistry", "Physics"):
            raise ValueError("Domínio GPQA inválido.")
        options = dict(zip("ABCD", (choices[index] for index in permutation)))
        return BenchmarkQuestion(
            id=f"GPQA_diamond_{record_id}", subject=domain.lower(), options=options,
            statement=statement + "\n" + "\n".join(f"{letter}) {text}" for letter, text in options.items()),
            expected_alternative="ABCD"[permutation.index(0)],
        )
