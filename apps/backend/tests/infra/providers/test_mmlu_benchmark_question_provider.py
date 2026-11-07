import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from src.infra.providers.mmlu_benchmark_question_provider import MMLUBenchmarkQuestionProvider, MMLU_REVISION


def _record(subject: str, split: str, index: int = 0) -> dict:
    return {
        "id": f"MMLU_{subject}_{split}_{index:04d}", "subject": subject,
        "question": f"{split} {subject} {index}\u2028preservado", "choices": ["um", "dois", "três", "quatro"],
        "answer": 1,
    }


def _write_dataset(directory: Path, test: list[dict], dev: list[dict]) -> None:
    manifest = {"revision": MMLU_REVISION, "files": {}}
    for split, records in (("test", test), ("dev", dev)):
        content = ("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n").encode("utf-8")
        (directory / f"{split}.jsonl").write_bytes(content)
        manifest["files"][split] = {
            "sha256": hashlib.sha256(content).hexdigest(), "count": len(records),
            "subjects": dict(Counter(record["subject"] for record in records)),
        }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    _write_dataset(
        tmp_path,
        [_record(subject, "test") for subject in ("physics", "history")],
        [_record(subject, "dev", i) for subject in ("physics", "history") for i in range(5)],
    )
    return tmp_path


def test_corpus_oficial_local_tem_14042_testes_e_57_disciplinas() -> None:
    provider = MMLUBenchmarkQuestionProvider()
    questions = provider.list_questions()
    assert len(questions) == 14042
    assert len({q.subject for q in questions}) == 57
    assert all(list(q.options) == list("ABCD") for q in questions)
    assert len({q.id for q in questions}) == len(questions)
    assert all("_test_" in q.id for q in questions)


@pytest.mark.parametrize("few_shot", [0, 5])
def test_prompt_preserva_enunciado_e_gabarito_do_teste_fica_fora(dataset: Path, few_shot: int) -> None:
    provider = MMLUBenchmarkQuestionProvider(few_shot, dataset)
    question = next(q for q in provider.list_questions() if q.subject == "physics")
    prompt = provider.build_prompt(question, provider.answer_instruction())
    assert question.statement in prompt
    assert "\u2028preservado" in prompt
    assert "test physics 0" in prompt
    assert prompt.count("Answer: B") == few_shot
    assert prompt.count("dev physics") == few_shot
    assert "dev history" not in prompt
    assert "E," not in provider.answer_instruction()
    assert provider.definition().protocol == f"generative_{few_shot}shot"
    assert provider.definition().revision == MMLU_REVISION
    assert provider.list_questions() == provider.list_questions()


def test_build_prompt_carrega_dataset_quando_ainda_nao_foi_lido(dataset: Path) -> None:
    provider = MMLUBenchmarkQuestionProvider(5, dataset)
    question = MMLUBenchmarkQuestionProvider(0, dataset).list_questions()[0]
    assert "Answer: B" in provider.build_prompt(question, "instrução")


def test_lista_devolvida_nao_altera_o_cache(dataset: Path) -> None:
    provider = MMLUBenchmarkQuestionProvider(data_path=dataset)
    provider.list_questions().clear()
    assert len(provider.list_questions()) == 2


@pytest.mark.parametrize("few_shot", [-1, 1, 4, 6])
def test_rejeita_numero_de_exemplos_nao_suportado(few_shot: int) -> None:
    with pytest.raises(ValueError, match="0 ou 5"):
        MMLUBenchmarkQuestionProvider(few_shot)


def test_dataset_ausente_e_erro_explicito(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ausente ou inválido"):
        MMLUBenchmarkQuestionProvider(data_path=tmp_path).list_questions()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda m: m.update(revision="outra"), "Revisão"),
        (lambda m: m["files"]["test"].update(sha256="alterado"), "Hash"),
        (lambda m: m["files"]["test"].update(count=8), "Contagem"),
        (lambda m: m["files"]["test"].update(subjects={}), "Contagem"),
    ],
)
def test_rejeita_divergencia_do_manifesto(dataset: Path, mutation, message: str) -> None:
    path = dataset / "manifest.json"
    manifest = json.loads(path.read_text("utf-8"))
    mutation(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        MMLUBenchmarkQuestionProvider(data_path=dataset).list_questions()


def test_rejeita_identificadores_duplicados(dataset: Path) -> None:
    _write_dataset(dataset, [_record("physics", "test")] * 2, [_record("physics", "dev", i) for i in range(5)])
    with pytest.raises(ValueError, match="duplicados"):
        MMLUBenchmarkQuestionProvider(data_path=dataset).list_questions()


@pytest.mark.parametrize("dev", [[], [_record("physics", "dev", i) for i in range(4)]])
def test_rejeita_exemplos_insuficientes(dataset: Path, dev: list[dict]) -> None:
    _write_dataset(dataset, [_record("physics", "test")], dev)
    with pytest.raises(ValueError, match="cinco exemplos"):
        MMLUBenchmarkQuestionProvider(data_path=dataset).list_questions()


@pytest.mark.parametrize("overrides", [
    {"choices": "ABCD"}, {"choices": ["a"]}, {"choices": ["a", "b", "c", ""]},
    {"answer": True}, {"answer": -1}, {"answer": 4}, {"subject": ""}, {"subject": 9},
    {"question": " "}, {"question": 9}, {"id": "MMLU_physics_dev_0000"}, {"id": 9},
])
def test_rejeita_registros_invalidos(dataset: Path, overrides: dict) -> None:
    record = {**_record("physics", "test"), **overrides}
    _write_dataset(dataset, [record], [_record("physics", "dev", i) for i in range(5)])
    with pytest.raises(ValueError, match="Registro MMLU inválido"):
        MMLUBenchmarkQuestionProvider(data_path=dataset).list_questions()


def test_json_invalido_e_diagnosticado(dataset: Path) -> None:
    (dataset / "manifest.json").write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="ausente ou inválido"):
        MMLUBenchmarkQuestionProvider(data_path=dataset).list_questions()
