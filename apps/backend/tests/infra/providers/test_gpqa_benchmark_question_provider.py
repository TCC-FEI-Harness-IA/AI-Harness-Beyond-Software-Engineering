import csv
import hashlib
import io
import json
import random
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pytest

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.infra.providers.gpqa_benchmark_question_provider import GPQABenchmarkQuestionProvider, GPQA_REVISION


def _record(index: int = 0) -> dict:
    return {
        "Record ID": f"synthetic{index}", "Question": "Questão sintética\ncom Unicode \u2028 preservado",
        "High-level domain": "Physics", "Correct Answer": "correta",
        "Incorrect Answer 1": "incorreta 1", "Incorrect Answer 2": "incorreta 2", "Incorrect Answer 3": "incorreta 3",
        "Explanation": "EXPLICACAO_PRIVADA", "Pre-Revision Question": "REVISAO_ANTIGA",
    }


def _write_dataset(path: Path, records: list[dict]) -> None:
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    content = text.getvalue().encode("utf-8")
    with ZipFile(path / "dataset.zip", "w") as archive:
        for subset in ("diamond", "main", "extended"):
            archive.writestr(f"dataset/gpqa_{subset}.csv", content)
    manifest = {
        "revision": GPQA_REVISION, "choice_seed": 0,
        "archive_sha256": hashlib.sha256((path / "dataset.zip").read_bytes()).hexdigest(),
        "subsets": {subset: {"sha256": hashlib.sha256(content).hexdigest(), "count": len(records),
                             "subjects": {"physics": len(records)}}
                    for subset in ("diamond", "main", "extended")},
    }
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    _write_dataset(tmp_path, [_record(i) for i in range(4)])
    return tmp_path


@pytest.mark.parametrize("subset,count,subjects", [
    ("diamond", 198, {"biology": 19, "chemistry": 93, "physics": 86}),
    ("main", 448, {"biology": 78, "chemistry": 183, "physics": 187}),
    ("extended", 546, {"biology": 105, "chemistry": 214, "physics": 227}),
])
def test_corpus_oficial_protegido_por_subconjunto(subset: str, count: int, subjects: dict) -> None:
    provider = GPQABenchmarkQuestionProvider(subset=subset)
    questions = provider.list_questions()
    assert len(questions) == len({q.id for q in questions}) == count
    assert Counter(q.subject for q in questions) == subjects
    assert all(list(q.options) == list("ABCD") for q in questions)
    assert set(q.expected_alternative for q in questions) == set("ABCD")
    assert all(q.id.startswith(f"GPQA_{subset}_") for q in questions)
    definition = provider.definition()
    assert definition.dataset is BenchmarkDatasetEnum.GPQA
    assert definition.revision == GPQA_REVISION
    assert (definition.split, definition.protocol, definition.few_shot) == (subset, "generative_0shot", 0)


@pytest.mark.parametrize("subset", ["diamond", "main", "extended"])
def test_permutacao_reproduzivel_preserva_gabarito_e_prompt_sem_metadados(dataset: Path, subset: str) -> None:
    provider = GPQABenchmarkQuestionProvider(data_path=dataset, subset=subset)
    questions = provider.list_questions()
    rng = random.Random(0)
    for question in questions:
        permutation = rng.sample(range(4), 4)
        assert question.expected_alternative == "ABCD"[permutation.index(0)]
        assert question.options[question.expected_alternative] == "correta"
        prompt = provider.build_prompt(question, provider.answer_instruction())
        assert question.statement in prompt
        assert "\u2028 preservado" in prompt
        assert f"FINAL_ANSWER: {question.expected_alternative}" not in prompt
        assert "EXPLICACAO_PRIVADA" not in prompt
        assert "REVISAO_ANTIGA" not in prompt
        assert "FINAL_ANSWER: LETTER" in prompt
        assert "RESPOSTA_FINAL" not in prompt
    assert questions == GPQABenchmarkQuestionProvider(data_path=dataset, subset=subset).list_questions()
    provider.list_questions().clear()
    assert provider.list_questions() == questions


@pytest.mark.parametrize("few_shot", [-1, 1, 5])
def test_rejeita_few_shot(few_shot: int) -> None:
    with pytest.raises(ValueError, match="somente few_shot 0"):
        GPQABenchmarkQuestionProvider(few_shot)


def test_dataset_ausente_e_recusado(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ausente ou inválido"):
        GPQABenchmarkQuestionProvider(data_path=tmp_path).list_questions()


@pytest.mark.parametrize("mutation,message", [
    ({"revision": "outra"}, "Revisão"), ({"choice_seed": 42}, "semente"),
    ({"archive_sha256": "alterado"}, "Hash do arquivo"), ({"sha256": "alterado"}, "Hash do CSV"),
    ({"count": 99}, "Contagem"), ({"subjects": {}}, "Contagem"),
])
def test_confere_integridade(dataset: Path, mutation: dict, message: str) -> None:
    path = dataset / "manifest.json"
    manifest = json.loads(path.read_text())
    target = manifest["subsets"]["diamond"] if set(mutation) & {"sha256", "count", "subjects"} else manifest
    target.update(mutation)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=message):
        GPQABenchmarkQuestionProvider(data_path=dataset).list_questions()


@pytest.mark.parametrize("mutation,message", [
    ({"Question": " "}, "Registro"), ({"Record ID": ""}, "Registro"),
    ({"Incorrect Answer 1": ""}, "Registro"), ({"High-level domain": "Math"}, "Domínio"),
])
def test_rejeita_registro_invalido(dataset: Path, mutation: dict, message: str) -> None:
    _write_dataset(dataset, [_record() | mutation])
    with pytest.raises(ValueError, match=message):
        GPQABenchmarkQuestionProvider(data_path=dataset).list_questions()


def test_rejeita_ids_duplicados(dataset: Path) -> None:
    _write_dataset(dataset, [_record(), _record()])
    with pytest.raises(ValueError, match="duplicados"):
        GPQABenchmarkQuestionProvider(data_path=dataset).list_questions()


def test_preserva_distratores_duplicados_presentes_no_original(dataset: Path) -> None:
    _write_dataset(dataset, [_record() | {"Incorrect Answer 2": "incorreta 1"}])
    question = GPQABenchmarkQuestionProvider(data_path=dataset).list_questions()[0]
    assert list(question.options.values()).count("incorreta 1") == 2


def test_rejeita_subconjunto_desconhecido() -> None:
    with pytest.raises(ValueError):
        GPQABenchmarkQuestionProvider(subset="unknown")


def test_instrucao_propria_do_gpqa_e_em_ingles_e_lida_uma_vez(tmp_path: Path) -> None:
    instrucao = tmp_path / "gpqa.md"
    instrucao.write_text("\n  Answer.  \n", encoding="utf-8")
    provider = GPQABenchmarkQuestionProvider(prompt_path=instrucao)

    assert provider.answer_instruction() == "Answer."
    instrucao.write_text("Other", encoding="utf-8")
    assert provider.answer_instruction() == "Answer."
    oficial = GPQABenchmarkQuestionProvider().answer_instruction()
    assert "Reason carefully before answering." in oficial
    assert oficial.endswith("FINAL_ANSWER: LETTER")


def test_instrucao_do_gpqa_ausente_e_recusada(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="não encontrada"):
        GPQABenchmarkQuestionProvider(prompt_path=tmp_path / "nada.md").answer_instruction()
