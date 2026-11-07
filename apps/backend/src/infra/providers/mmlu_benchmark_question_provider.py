import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider

MMLU_REVISION = "c30699e8356da336a370243923dbaf21066bb9fe"
_DATA_PATH = Path(__file__).resolve().parents[1] / "benchmark/mmlu"
_LETTERS = "ABCD"
_INSTRUCTION = (
    "Solve the multiple-choice question above. Select exactly one of A, B, C, or D, preserving the original order. "
    "You may explain your reasoning, but end your response with a single line in this exact format: "
    "RESPOSTA_FINAL: LETTER (replace LETTER with your selected letter)."
)


class MMLUBenchmarkQuestionProvider(IBenchmarkQuestionProvider):
    """MMLU local, versionado e generativo; exemplos vêm exclusivamente do split dev."""

    def __init__(self, few_shot: int = 0, data_path: Path = _DATA_PATH) -> None:
        if few_shot not in (0, 5):
            raise ValueError("MMLU aceita few_shot 0 ou 5.")
        self.few_shot = few_shot
        self.data_path = data_path
        self._questions: list[BenchmarkQuestion] | None = None
        self._examples: dict[str, list[BenchmarkQuestion]] = defaultdict(list)

    def definition(self) -> BenchmarkDefinition:
        return BenchmarkDefinition(
            dataset=BenchmarkDatasetEnum.MMLU, revision=MMLU_REVISION,
            protocol=f"generative_{self.few_shot}shot", few_shot=self.few_shot,
        )

    def answer_instruction(self) -> str:
        return _INSTRUCTION

    def list_questions(self) -> list[BenchmarkQuestion]:
        if self._questions is None:
            try:
                manifest = json.loads((self.data_path / "manifest.json").read_text("utf-8"))
                if manifest["revision"] != MMLU_REVISION:
                    raise ValueError("Revisão MMLU incompatível.")
                questions = self._load_split("test", manifest)
                examples = self._load_split("dev", manifest)
                grouped: dict[str, list[BenchmarkQuestion]] = defaultdict(list)
                for example in examples:
                    grouped[example.subject].append(example)
                if set(grouped) != {q.subject for q in questions} or any(len(q) != 5 for q in grouped.values()):
                    raise ValueError("MMLU requer cinco exemplos dev por disciplina de teste.")
                self._examples = grouped
                self._questions = sorted(questions, key=lambda question: question.id)
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError(f"Dataset MMLU local ausente ou inválido: {error}") from error
        return list(self._questions)

    def build_prompt(self, question: BenchmarkQuestion, instruction: str) -> str:
        if self._questions is None:
            self.list_questions()
        subject = question.subject.replace("_", " ")
        parts = [f"The following are multiple choice questions (with answers) about {subject}."]
        for example in self._examples[question.subject][:self.few_shot]:
            parts.append(f"{example.statement}\nAnswer: {example.expected_alternative}")
        parts.append(f"{question.statement}\nAnswer:")
        parts.append(instruction)
        return "\n\n".join(parts)

    def _load_split(self, split: str, manifest: dict) -> list[BenchmarkQuestion]:
        content = (self.data_path / f"{split}.jsonl").read_bytes()
        metadata = manifest["files"][split]
        if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise ValueError(f"Hash do split MMLU {split} difere do manifesto.")
        questions = [self._question(json.loads(line), split) for line in content.decode("utf-8").split("\n") if line]
        counts = Counter(question.subject for question in questions)
        if len(questions) != metadata["count"] or counts != metadata["subjects"]:
            raise ValueError(f"Contagem do split MMLU {split} difere do manifesto.")
        if len({q.id for q in questions}) != len(questions):
            raise ValueError(f"Identificadores duplicados no split MMLU {split}.")
        return questions

    @staticmethod
    def _question(record: dict, split: str) -> BenchmarkQuestion:
        choices, answer, subject = record["choices"], record["answer"], record["subject"]
        if (
            not isinstance(choices, list) or len(choices) != 4
            or not all(isinstance(value, str) and value.strip() for value in choices)
            or type(answer) is not int or not 0 <= answer < 4
            or not isinstance(subject, str) or not subject
            or not isinstance(record["question"], str) or not record["question"].strip()
            or not isinstance(record["id"], str)
            or not record["id"].startswith(f"MMLU_{subject}_{split}_")
        ):
            raise ValueError("Registro MMLU inválido.")
        options = dict(zip(_LETTERS, choices))
        statement = record["question"] + "\n" + "\n".join(f"{letter}) {text}" for letter, text in options.items())
        return BenchmarkQuestion(
            id=record["id"], statement=statement, options=options,
            expected_alternative=_LETTERS[answer], subject=subject,
        )
