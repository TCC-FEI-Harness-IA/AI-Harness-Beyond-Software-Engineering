"""Integridade do corpus real e da proveniência arquivada, sem acesso à rede."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[3] / "src/infra/benchmark"
QUESTIONS = BASE / "questions"
MANIFEST = json.loads((BASE / "sources/manifest.json").read_text(encoding="utf-8"))
KEYS = json.loads((BASE / "sources/official_answer_keys.json").read_text(encoding="utf-8"))


def _normalizar(texto: str) -> str:
    """Ignora numeração, contexto comum, acentos, caixa, espaços e pontuação."""
    texto = texto.rsplit("### Enunciado", 1)[-1]
    texto = re.sub(r"^# QUESTÃO \d+\s*", "", texto)
    texto = unicodedata.normalize("NFKD", texto).casefold()
    return "".join(letra for letra in texto if letra.isalnum())


def test_totais_disciplinas_instituicoes_e_anos() -> None:
    registros = MANIFEST["questions"]
    assert len(registros) == len({item["id"] for item in registros}) == 90
    assert Counter(item["discipline"] for item in registros) == {"FISICA": 30, "MATEMATICA": 30, "QUIMICA": 30}
    assert {item["id"] for item in registros} == {path.name for path in QUESTIONS.iterdir() if path.is_dir()}
    for disciplina in ("FISICA", "MATEMATICA", "QUIMICA"):
        selecao = [item for item in registros if item["discipline"] == disciplina]
        assert {item["exam"] for item in selecao} == {"ENEM", "FUVEST", "ITA", "UNICAMP"}
        assert len({item["year"] for item in selecao}) >= 3


def test_todas_as_questoes_tem_arquivos_e_gabarito_oficial_sem_orfaos() -> None:
    for item in MANIFEST["questions"]:
        pasta = QUESTIONS / item["id"]
        assert {path.name for path in pasta.iterdir()} == {"enunciado.md", "alternativa_correta.md"}
        enunciado = (pasta / "enunciado.md").read_text(encoding="utf-8")
        resposta = (pasta / "alternativa_correta.md").read_text(encoding="utf-8").strip()
        alternativas = dict(re.findall(r"^([A-E])\) (.+)$", enunciado, re.MULTILINE))
        letra = KEYS[item["source_id"]][str(item["original_number"])]
        assert letra is not None
        assert letra == item["official_answer"] == resposta[0]
        assert resposta == f"{letra}) {alternativas[letra]}"
        assert len(alternativas) == item["option_count"] == (4 if item["exam"] == "UNICAMP" else 5)
        assert hashlib.sha256((pasta / "enunciado.md").read_bytes()).hexdigest() == item["statement_sha256"]
        assert hashlib.sha256((pasta / "alternativa_correta.md").read_bytes()).hexdigest() == item["answer_sha256"]
        fonte = MANIFEST["sources"][item["source_id"]]
        assert fonte["exam"] == item["exam"] and fonte["year"] == item["year"]
        assert item["id"].startswith(f"{item['discipline']}_{fonte['exam']}_{fonte['year']}_")
        assert item["id"].endswith(f"Q{item['original_number']:03d}")
        assert all(pagina > 0 for pagina in item["proof_pages"])


def test_provas_e_gabaritos_arquivados_integros_e_com_urls_oficiais() -> None:
    dominios = {"ENEM": "download.inep.gov.br", "FUVEST": "www.fuvest.br",
                "ITA": "vestibular.ita.br", "UNICAMP": "www.comvest.unicamp.br"}
    arquivos = set()
    assert set(KEYS) == set(MANIFEST["sources"]) == {item["source_id"] for item in MANIFEST["questions"]}
    for fonte in MANIFEST["sources"].values():
        assert fonte["phase"] and fonte["booklet"] and fonte["date"]
        for tipo in ("proof", "key"):
            url = urlparse(fonte[tipo])
            assert url.scheme == "https" and url.hostname == dominios[fonte["exam"]]
            arquivo = BASE / fonte[f"{tipo}_file"]
            arquivos.add(arquivo.name)
            dados = arquivo.read_bytes()
            assert dados.startswith(b"%PDF-")
            assert hashlib.sha256(dados).hexdigest() == fonte[f"{tipo}_sha256"]
    assert arquivos == {path.name for path in (BASE / "sources").glob("*.pdf")}


def test_nao_ha_questoes_duplicadas_mesmo_com_formatacao_diferente() -> None:
    textos = [
        _normalizar((QUESTIONS / item["id"] / "enunciado.md").read_text(encoding="utf-8"))
        for item in MANIFEST["questions"]
    ]
    assert len(set(textos)) == 90
    origens = [(item["source_id"], item["original_number"]) for item in MANIFEST["questions"]]
    assert len(set(origens)) == 90
    # Uma transcrição copiada com uma pequena inserção também deve ser investigada.
    for primeiro, segundo in combinations(textos, 2):
        assert primeiro not in segundo and segundo not in primeiro


def test_nao_ha_recursos_ausentes_ou_ruido_de_extracao() -> None:
    for arquivo in QUESTIONS.glob("*/enunciado.md"):
        texto = arquivo.read_text(encoding="utf-8")
        assert not any(unicodedata.category(letra) in {"Co", "Cs"} for letra in texto), arquivo
        assert not any(ord(letra) < 32 and letra not in "\n\t" for letra in texto), arquivo
        assert not re.search(r"ENEM20\d{2}ENEM|PAGE \d|\*\d+AZ\d+\*", texto), arquivo
        assert not re.search(r"\b(?:figura|gráfico|esquema|imagem) (?:a seguir|abaixo|anterior)", texto), arquivo
        for recurso in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texto):
            assert (arquivo.parent / recurso).is_file(), (arquivo, recurso)


def test_as_quinze_questoes_originais_continuam_identificadas() -> None:
    originais = {
        "FISICA": [108, 112, 113, 122, 124],
        "MATEMATICA": [137, 138, 139, 141, 143],
        "QUIMICA": [94, 96, 102, 118, 126],
    }
    preservadas = {
        item["id"] for item in MANIFEST["questions"]
        if "Questão preexistente preservada byte a byte." in item["notes"]
    }
    assert preservadas == {
        f"{disciplina}_ENEM_2023_AZUL_Q{numero:03d}"
        for disciplina, numeros in originais.items() for numero in numeros
    }
    hashes = json.loads((BASE / "sources/preserved_originals.json").read_text(encoding="utf-8"))
    assert len(hashes) == 30
    for caminho, esperado in hashes.items():
        relativo = caminho.split("src/infra/benchmark/", 1)[1]
        assert hashlib.sha256((BASE / relativo).read_bytes()).hexdigest() == esperado
