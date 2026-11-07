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
from src.domain.enums.gpqa_subset_enum import GPQASubsetEnum
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.infra.providers.benchmark_instruction_reader import BENCHMARK_PROMPTS_PATH, read_benchmark_instruction

GPQA_REVISION = "56686c06f5e19865c153de0fdb11be3890014df7"
GPQA_CHOICE_SEED = 0
_DATA_PATH = Path(__file__).resolve().parents[1] / "benchmark/gpqa"
_PASSWORD = b"deserted-untie-orchid"  # Senha pública fornecida pelos autores.
_PROMPT_PATH = BENCHMARK_PROMPTS_PATH / "gpqa.md"


class GPQABenchmarkQuestionProvider(IBenchmarkQuestionProvider):
    """GPQA local: subconjunto oficial protegido, zero exemplos e permutação fixa de alternativas."""

    def __init__(
        self, few_shot: int = 0, data_path: Path = _DATA_PATH,
        subset: GPQASubsetEnum = GPQASubsetEnum.DIAMOND, prompt_path: Path = _PROMPT_PATH,
    ) -> None:
        if few_shot != 0:
            raise ValueError("GPQA aceita somente few_shot 0.")
        self.subset = GPQASubsetEnum(subset)
        self.data_path = data_path
        self.prompt_path = prompt_path
        self._instruction: str | None = None
        self._questions: list[BenchmarkQuestion] | None = None

    def definition(self) -> BenchmarkDefinition:
        return BenchmarkDefinition(
            dataset=BenchmarkDatasetEnum.GPQA, revision=GPQA_REVISION,
            protocol="generative_0shot", split=self.subset.value,
        )

    def answer_instruction(self) -> str:
        if self._instruction is None:
            self._instruction = read_benchmark_instruction(path=self.prompt_path)
        return self._instruction

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
        metadata = manifest["subsets"][self.subset.value]
        with ZipFile(io.BytesIO(archive)) as source:
            content = source.read(f"dataset/gpqa_{self.subset.value}.csv", pwd=_PASSWORD)
        if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise ValueError(f"Hash do CSV GPQA {self.subset.value} difere do manifesto.")
        # A permutação ocorre no corpus inteiro antes de filtros/amostras, preservando reruns e exports.
        rng = random.Random(GPQA_CHOICE_SEED)
        records = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        questions = [self._question(record, rng.sample(range(4), 4)) for record in records]
        if len(questions) != metadata["count"] or Counter(q.subject for q in questions) != metadata["subjects"]:
            raise ValueError(f"Contagem GPQA {self.subset.value} difere do manifesto.")
        if len({q.id for q in questions}) != len(questions):
            raise ValueError("Identificadores GPQA duplicados.")
        return sorted(questions, key=lambda question: question.id)

    def _question(self, record: dict, permutation: list[int]) -> BenchmarkQuestion:
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
            id=f"GPQA_{self.subset.value}_{record_id}", subject=domain.lower(), options=options,
            statement=statement + "\n" + "\n".join(f"{letter}) {text}" for letter, text in options.items()),
            expected_alternative="ABCD"[permutation.index(0)],
        )
