"""Re-extract official answer keys from the archived PDFs (requires PyMuPDF).

Run from apps/backend: python scripts/verify_benchmark_sources.py
This is an audit tool, not a backend/runtime dependency. It does not use the network.
"""
import hashlib
import json
import re
from pathlib import Path

import pymupdf

BASE = Path(__file__).resolve().parents[1] / "src/infra/benchmark"


def extract_key(source_id: str, path: Path) -> dict[str, str | None]:
    """Read the exact booklet represented in the manifest, retaining annulments as null."""
    with pymupdf.open(path) as document:
        if source_id == "fuvest24":
            # Page 1, two columns under PROVA V only. The old D is struck out on Q48;
            # the last printed letter is the final corrected answer E.
            text = document[0].get_text(clip=pymupdf.Rect(20, 170, 135, 800))
            return {
                number: letters.split()[-1]
                for number, letters in re.findall(r"\b(\d{1,2})\s+([A-E](?:\s+[A-E])?)", text)
            }
        text = "\n".join(page.get_text() for page in document)
    return {
        str(int(number)): letter if letter in "ABCDE" else None
        for number, letter in re.findall(r"\b(\d{1,3})\s+([A-E]\b|[Aa]nulad[ao]|\(\*\)|\*)", text)
    }


def main() -> None:
    manifest = json.loads((BASE / "sources/manifest.json").read_text(encoding="utf-8"))
    recorded = json.loads((BASE / "sources/official_answer_keys.json").read_text(encoding="utf-8"))
    extracted = {}
    for source_id, source in manifest["sources"].items():
        for kind in ("proof", "key"):
            path = BASE / source[f"{kind}_file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source[f"{kind}_sha256"], path
        extracted[source_id] = extract_key(source_id, BASE / source["key_file"])
        assert extracted[source_id] == recorded[source_id], f"Official key transcript differs: {source_id}"
        with pymupdf.open(BASE / source["proof_file"]) as proof:
            for question in manifest["questions"]:
                if question["source_id"] == source_id:
                    assert all(1 <= page <= len(proof) for page in question["proof_pages"]), question["id"]
        print(f"{source_id}: PDFs intactos; {len(extracted[source_id])} respostas oficiais conferidas")
    for question in manifest["questions"]:
        expected = extracted[question["source_id"]][str(question["original_number"])]
        answer = (BASE / "questions" / question["id"] / "alternativa_correta.md").read_text(encoding="utf-8")
        assert expected is not None, f"Annulled question: {question['id']}"
        assert expected == question["official_answer"] == answer[0], question["id"]
    print(f"OK: {len(manifest['questions'])} gabaritos correspondem aos PDFs oficiais definitivos.")


if __name__ == "__main__":
    main()
