"""Recalcula a análise a partir dos CSVs e ZIPs, sem dependências externas.

Uso: python3 analise/reproduzir_analise.py --output /tmp/metricas-ralph.json
Os arquivos de entrada nunca são alterados. Datas e gabaritos permanecem os originais.
"""

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile


ROOT = Path(__file__).resolve().parent
BIO = {
    "BIOLOGIA", "biology", "college_biology", "high_school_biology", "anatomy",
    "clinical_knowledge", "college_medicine", "human_aging", "human_sexuality",
    "medical_genetics", "nutrition", "professional_medicine", "virology",
}
SOCIAL_OTHER = {"business_ethics", "management", "marketing", "professional_accounting"}
GENERAL = {"global_facts", "miscellaneous"}
FAMILIES = {
    "Física": {"physics", "FISICA", "college_physics", "high_school_physics", "conceptual_physics"},
    "Química": {"chemistry", "QUIMICA", "college_chemistry", "high_school_chemistry"},
    "Biologia estrita": {"BIOLOGIA", "biology", "college_biology", "high_school_biology"},
    "Matemática e estatística": {"MATEMATICA", "abstract_algebra", "college_mathematics",
                               "elementary_mathematics", "high_school_mathematics", "high_school_statistics"},
}


def area3(row):
    if row["materia"] in BIO:
        return "Biológicas e saúde"
    if row["materia"] in GENERAL:
        return "Geral/interdisciplinar"
    if row["area"] == "Exatas e biológicas (STEM)":
        return "Exatas e tecnologia"
    assert row["area"] in {"Humanidades", "Ciências sociais"} or row["materia"] in SOCIAL_OTHER
    return "Humanas e sociais"


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ["simples_correta", "simples_falha", "ralph_correta", "ralph_falha"]:
            assert row[key] in {"true", "false"}
            row[key] = row[key] == "true"
        for key in ["simples_tokens", "ralph_tokens", "quartil_tokens_simples", "quartil_tokens_ralph"]:
            row[key] = int(row[key])
        for key in ["simples_segundos", "ralph_segundos"]:
            row[key] = float(row[key])
        row["area_reagrupada"] = area3(row)
        for flow in ["simples", "ralph"]:
            assert not row[flow+"_falha"] or not row[flow+"_correta"]
            if not row[flow+"_falha"]:
                assert row[flow+"_correta"] == (row[flow+"_alternativa"] == row["gabarito"])
        expected = ("both_correct" if row["ralph_correta"] else "ralph_regresses") if row["simples_correta"] else ("ralph_recovers" if row["ralph_correta"] else "both_wrong")
        assert row["desfecho"] == expected
    assert len({(r["benchmark_session_id"], r["question_id"]) for r in rows}) == len(rows)
    return rows


def p_exact(b, c):
    return min(1, 2 * sum(math.comb(b+c, k) for k in range(min(b,c)+1)) / 2**(b+c))


def wilson(k, n):
    z = 1.959963984540054
    p = k/n
    den = 1+z*z/n
    mid = (p+z*z/(2*n))/den
    margin = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-margin, mid+margin]


def describe(values):
    s = sorted(values)
    def quantile(q):
        i = (len(s)-1)*q
        lo = math.floor(i)
        return s[lo] + (s[min(lo+1,len(s)-1)]-s[lo])*(i-lo)
    return {"sum": sum(s), "mean": statistics.mean(s), "median": statistics.median(s),
            "p90": quantile(.9), "p95": quantile(.95), "max": max(s)}


def summary(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    outcomes = collections.Counter(r["desfecho"] for r in rows)
    sc = sum(r["simples_correta"] for r in rows)
    rc = sum(r["ralph_correta"] for r in rows)
    b, c = outcomes["ralph_regresses"], outcomes["ralph_recovers"]
    result = {"n": n, "simple_correct": sc, "ralph_correct": rc, "simple_accuracy": sc/n,
              "ralph_accuracy": rc/n, "delta_pp": (rc-sc)/n*100, "net": rc-sc,
              "recoveries": c, "regressions": b, "both_correct": outcomes["both_correct"],
              "both_wrong": outcomes["both_wrong"], "mcnemar_p": p_exact(b,c),
              "recovery_rate": c/(n-sc) if n>sc else None,
              "regression_rate": b/sc if sc else None,
              "simple_failure": sum(r["simples_falha"] for r in rows),
              "ralph_failure": sum(r["ralph_falha"] for r in rows),
              "simple_ci": wilson(sc,n), "ralph_ci": wilson(rc,n),
              "both_wrong_same": sum(r["desfecho"] == "both_wrong" and r["simples_alternativa"] == r["ralph_alternativa"] for r in rows)}
    # IC normal aproximado da média das diferenças pareadas {-1,0,1}.
    se = math.sqrt(((b+c)-(c-b)**2/n)/(n-1)/n)
    result["paired_delta_ci_pp_approx"] = [(c-b)/n*100-1.959963984540054*se*100,
                                            (c-b)/n*100+1.959963984540054*se*100]
    for field in ["simples_tokens", "ralph_tokens", "simples_segundos", "ralph_segundos"]:
        result[field] = describe([r[field] for r in rows])
    result["token_ratio"] = result["ralph_tokens"]["sum"] / result["simples_tokens"]["sum"]
    result["time_ratio"] = result["ralph_segundos"]["sum"] / result["simples_segundos"]["sum"]
    return result


def grouped(rows, field):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: summary(value) for key,value in sorted(groups.items())}


def load_logs(all_rows):
    index = {(r["benchmark_session_id"], r["question_id"]): r for r in all_rows}
    logs = []
    for path in sorted(ROOT.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith("/execucao-ralph-loop.json"):
                    continue
                doc = json.loads(archive.read(name))
                s = doc["session"]
                row = index[(doc["benchmark_session_id"], doc["question_id"])]
                assert not row["ralph_correta"]
                assert doc["outcome"]["total_tokens"] == row["ralph_tokens"]
                assert (doc["outcome"]["error"] is not None) == row["ralph_falha"]
                failure = s.get("failure") or {}
                kind = failure.get("limit") or ("format_final" if doc["outcome"]["error"] and not failure else failure.get("reason", "wrong_answer"))
                if kind == "technical_error":
                    kind = "provider_credit" if "HTTP 403" in failure["description"] else "parse_or_schema"
                msgs = s["messages"]
                counts = collections.Counter(m.get("subtype") for m in msgs)
                invs = s["invocations"]
                logs.append({"zip": path.name, "member": name, "question_id": doc["question_id"],
                             "benchmark": row["benchmark"], "materia": row["materia"],
                             "area": row["area_reagrupada"], "kind": kind,
                             "phase": failure.get("phase", "C3/avaliacao" if kind=="format_final" else None),
                             "simple_correct": row["simples_correta"], "simple_failure": row["simples_falha"],
                             "ralph_failure": row["ralph_falha"], "tokens": row["ralph_tokens"],
                             "seconds": row["ralph_segundos"], "status": s["status"],
                             "flow_version": s.get("flow_version"), "temperature": s["temperature"],
                             "model": s["model_name"], "max_tokens": s["max_tokens"],
                             "selected": row["ralph_alternativa"], "expected": row["gabarito"],
                             "verify_fail": counts["verify_fail"], "verify_pass": counts["verify_pass"],
                             "plan_rejected": counts["plan_rejected"], "message_subtypes": dict(counts),
                             "calls": len(invs), "input_tokens": sum(i["tokens_input"] or 0 for i in invs),
                             "output_tokens": sum(i["tokens_output"] or 0 for i in invs),
                             "unknown_usage_calls": sum(i["tokens_input"] is None or i["tokens_output"] is None for i in invs),
                             "invalid_invocations": sum(i.get("content_accepted") is False for i in invs),
                             "invocation_diagnostics": [{"phase": i["phase"], "finish_reason": i.get("finish_reason"),
                                 "accepted": i.get("content_accepted"), "diagnostic": i.get("output_diagnostic"),
                                 "recovery": i.get("recovery"), "recovers": i.get("recovers_invocation_id")}
                                 for i in invs if i.get("content_accepted") is False],
                             "final_answer": s["final_answer"]})
    assert len(logs) == sum(not r["ralph_correta"] for r in all_rows)
    assert len({l["question_id"] for l in logs}) == len(logs)
    return logs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    all_rows = read_csv("analise-benchmark-questoes_considera-erros.csv")
    clean = read_csv("analise-benchmark-questoes_desconsidera-erros.csv")
    expected_clean = [r for r in all_rows if not r["simples_falha"] and not r["ralph_falha"]]
    assert [(r["benchmark_session_id"],r["question_id"]) for r in expected_clean] == [(r["benchmark_session_id"],r["question_id"]) for r in clean]
    for a,b in zip(expected_clean,clean):
        assert all(a[k] == b[k] for k in a if not k.startswith("quartil_"))
    removed = [r for r in all_rows if r["simples_falha"] or r["ralph_falha"]]
    logs = load_logs(all_rows)
    original_reports = {"analise-benchmark-considera-erros.md", "analise-benchmark-desconsidera-erros.md"}
    result = {"source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(ROOT.iterdir()) if p.suffix in {".zip", ".csv"} or p.name in original_reports},
              "all": summary(all_rows), "clean": summary(clean), "removed": summary(removed),
              "logs": logs, "removed_rows": removed}
    for label,rows in [("all",all_rows),("clean",clean)]:
        result[label+"_groups"] = {field: grouped(rows,field) for field in
                                  ["benchmark", "materia", "area", "area_reagrupada", "nivel", "quartil_tokens_simples", "quartil_tokens_ralph", "desfecho"]}
        result[label+"_families"] = {family: summary([r for r in rows if r["materia"] in members])
                                     for family,members in FAMILIES.items()}
    result["failure_causes"] = {kind: {"n": len(ls), "tokens": sum(l["tokens"] for l in ls),
        "seconds": sum(l["seconds"] for l in ls), "simple_correct": sum(l["simple_correct"] for l in ls),
        "benchmarks": dict(collections.Counter(l["benchmark"] for l in ls))}
        for kind in sorted({l["kind"] for l in logs})
        for ls in [[l for l in logs if l["kind"] == kind]]}
    # Sensibilidade: manter os quartis da base completa ao remover falhas.
    result["clean_fixed_quartiles"] = {field: grouped(expected_clean,field)
        for field in ["quartil_tokens_simples", "quartil_tokens_ralph"]}
    result["quartile_cuts"] = {}
    for label,rows in [("all",all_rows),("clean",clean)]:
        cuts = {}
        for benchmark in sorted({r["benchmark"] for r in rows}):
            group = [r for r in rows if r["benchmark"] == benchmark]
            cuts[benchmark] = {}
            for flow in ["simples", "ralph"]:
                vals = sorted(r[flow+"_tokens"] for r in group)
                limits = [vals[math.ceil(q*len(vals))-1] for q in [.25,.5,.75]]
                cuts[benchmark][flow] = limits
                assert all(r["quartil_tokens_"+flow] == 1+sum(r[flow+"_tokens"]>x for x in limits) for r in group)
        result["quartile_cuts"][label] = cuts
    output = json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.write_text(output+"\n",encoding="utf-8")
        print(f"Verificado: {len(all_rows)} pares, {len(clean)} pares sem falha, {len(logs)} logs. Métricas: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
