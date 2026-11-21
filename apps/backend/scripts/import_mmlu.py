"""Converte os Parquets oficiais fixados em JSONL, sem dependências novas no backend.

Uso: python scripts/import_mmlu.py --source-dir /tmp/mmlu
O diretório deve conter test.parquet e dev.parquet da revisão abaixo.
PyArrow é necessário apenas para esta importação/auditoria.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

REVISION = "c30699e8356da336a370243923dbaf21066bb9fe"
SOURCE_SHA256 = {
    "test": "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7",
    "dev": "2b19bde1ed8ca6b482fb283abc90e8e0d9d228947029c0b91795d64b28b3bc3f",
}
DESTINATION = Path(__file__).resolve().parents[1] / "src/infra/benchmark/mmlu"


def main() -> None:
    import pyarrow.parquet as parquet

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": "cais/mmlu", "revision": REVISION, "license": "MIT", "files": {}}
    for split, expected_count in (("test", 14042), ("dev", 285)):
        source = args.source_dir / f"{split}.parquet"
        if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256[split]:
            raise ValueError(f"O Parquet {split} não corresponde à revisão oficial fixada.")
        records = parquet.read_table(source).to_pylist()
        counts = Counter(row["subject"] for row in records)
        if len(records) != expected_count or len(counts) != 57:
            raise ValueError(f"Contagem inesperada no split {split}")
        counters: Counter[str] = Counter()
        lines = []
        for row in records:
            subject = row["subject"]
            index = counters[subject]
            counters[subject] += 1
            record = {"id": f"MMLU_{subject}_{split}_{index:04d}", **row}
            lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        content = ("\n".join(lines) + "\n").encode("utf-8")
        (DESTINATION / f"{split}.jsonl").write_bytes(content)
        manifest["files"][split] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "count": len(records),
            "subjects": dict(sorted(counts.items())),
            "source_url": (
                f"https://huggingface.co/datasets/cais/mmlu/resolve/{REVISION}/all/"
                f"{split}-00000-of-00001.parquet"
            ),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    (DESTINATION / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
