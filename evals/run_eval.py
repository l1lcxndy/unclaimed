"""Run the Unclaimed eval: every case in cases.jsonl goes through the real /ask endpoint against the
fictional corpus in evals/corpus/, and gets graded by code (free, deterministic, no judge model).

    venv\\Scripts\\python.exe evals\\run_eval.py
    venv\\Scripts\\python.exe evals\\run_eval.py --variant v1

Writes evals/results/<fictional|real>/<variant>/{results.jsonl,errors.jsonl,traces/}."""
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
FLOW = HERE / "results" / "fictional"
STATE = {
    "metrics": [
        {"id": "pass", "label": "Pass", "kind": "binary"},
        {"id": "recall", "label": "Recall", "kind": "float"},
        {"id": "no_wrong", "label": "No wrong", "kind": "binary"},
        {"id": "cited", "label": "Cited", "kind": "float"},
        {"id": "asks_info", "label": "Asks info", "kind": "binary"},
    ],
    "perf_fields": [{"id": "latency_s", "label": "Latency (s)"}, {"id": "programs", "label": "Programs"}],
}


def load_cases(path=HERE / "cases.jsonl"):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def corpus_chunks():
    """Corpus .txt files split on <<<PAGE>>>, chunked exactly like ingest.py chunks PDF pages."""
    from rag.chunker import chunk_text

    chunks = []
    for path in sorted((HERE / "corpus").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        name = text.splitlines()[0].strip()
        for page, page_text in enumerate(text.split("<<<PAGE>>>"), start=1):
            for i, piece in enumerate(chunk_text(page_text)):
                chunks.append({"id": f"{path.stem}_p{page}_c{i}", "text": piece, "metadata": {
                    "program_name": name, "source_file": path.name, "page": page,
                    "region": "national", "category": "general"}})
    return chunks


def program_names():
    return {p.read_text(encoding="utf-8").splitlines()[0].strip() for p in (HERE / "corpus").glob("*.txt")}


def norm(name):
    return " ".join(name.casefold().split())


def grade(case, response, known):
    """Score one /ask response. Metrics that don't apply to a case are left out, not scored as 0."""
    programs = response.get("programs") or []
    returned = {norm(p["program_name"]) for p in programs}
    expected = {norm(n) for n in case["expected"]}
    forbidden = {norm(n) for n in case["forbidden"]}
    scores, notes = {}, []

    if expected:
        missed = expected - returned
        scores["recall"] = 1 - len(missed) / len(expected)
        if missed:
            notes.append("missed: " + ", ".join(sorted(missed)))

    wrong = returned & forbidden
    invented = returned - {norm(n) for n in known}
    if case.get("no_match") and returned:
        wrong = returned
    scores["no_wrong"] = 0 if (wrong or invented) else 1
    if wrong:
        notes.append("wrongly listed: " + ", ".join(sorted(wrong)))
    if invented:
        notes.append("invented: " + ", ".join(sorted(invented)))

    if programs:
        scores["cited"] = sum(bool(p.get("cited")) for p in programs) / len(programs)
        uncited = [p["program_name"] for p in programs if not p.get("cited")]
        if uncited:
            notes.append("unverified citation: " + ", ".join(uncited))

    if case.get("needs_info"):
        scores["asks_info"] = 1 if response.get("missing_info") else 0
        if not response.get("missing_info"):
            notes.append("did not ask for missing info")

    scores["pass"] = int(all(v == 1 for v in scores.values()))
    return scores, "; ".join(notes) or "all checks passed"


def wilson(passed, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = passed / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="baseline", help="baseline or v1, v2, ...")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--model", help="Ollama model to use (default: MODEL_NAME from .env)")
    parser.add_argument("--cases", help="comma-separated case ids to run (default: all)")
    parser.add_argument("--real", action="store_true",
                        help="use your own docs/*.pdf and docs/real_cases.jsonl (both kept out of git) instead of the fictional corpus")
    args = parser.parse_args()
    if args.model:
        os.environ["MODEL_NAME"] = args.model

    import tempfile

    from fastapi.testclient import TestClient

    import app as unclaimed
    from rag import store

    # Fresh throwaway store per run, so the user's real chroma_store/ is never touched.
    if args.real:
        from ingest import DOCS, build_chunks
        chunks, cases_path, flow = build_chunks(DOCS), DOCS / "real_cases.jsonl", FLOW.with_name("real")
    else:
        chunks, cases_path, flow = corpus_chunks(), HERE / "cases.jsonl", FLOW
    unclaimed.collection = store.get_collection(tempfile.mkdtemp(prefix="unclaimed-eval-"), reset=True)
    store.add(unclaimed.collection, chunks)
    client = TestClient(unclaimed.app)
    model = os.getenv("MODEL_NAME") or "qwen3:14b-q4_K_M"

    out = flow / args.variant
    (out / "traces").mkdir(parents=True, exist_ok=True)
    if not (flow / "_state.json").exists():
        (flow / "_state.json").write_text(json.dumps(STATE, indent=2), encoding="utf-8")
    results_path = out / "results.jsonl"
    done = set()
    if results_path.exists():
        done = {(r["prompt_id"], r["rep"]) for r in map(json.loads, results_path.read_text(encoding="utf-8").splitlines())}

    cases = load_cases(cases_path)
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    known = {c["metadata"]["program_name"] for c in chunks}

    for case in cases:
        for rep in range(args.reps):
            if (case["id"], rep) in done:
                continue
            started = time.time()
            res = client.post("/ask", json={"question": case["question"], "history": case.get("history", []),
                                              "region": case.get("region")})
            latency = round(time.time() - started, 1)
            if res.status_code != 200:
                with open(out / "errors.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"prompt_id": case["id"], "rep": rep, "class": "harness_or_serving_error",
                                        "http_status": res.status_code, "detail": res.text[:500], "model": model}) + "\n")
                print(f"{case['id']} rep{rep}: ERROR {res.status_code} {res.text[:120]}")
                continue
            body = res.json()
            scores, explanation = grade(case, body, known)
            transcript = [*({"role": t["role"], "content": t["content"]} for t in case.get("history", [])),
                          {"role": "user", "content": case["question"]},
                          {"role": "assistant", "content": json.dumps(body, indent=2, ensure_ascii=False)}]
            (out / "traces" / f"{case['id']}_rep{rep}.json").write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")
            row = {"prompt_id": case["id"], "rep": rep, "prompt": case["question"], "tags": case["tags"],
                   "status": "ok", "grade": scores, "explanation": {"pass": explanation},
                   "model": model, "latency_s": latency, "programs": len(body.get("programs") or []),
                   "meta": {"expected": case["expected"], "forbidden": case["forbidden"],
                            "returned": [p["program_name"] for p in body.get("programs") or []]}}
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{case['id']} rep{rep}: {'PASS' if scores['pass'] else 'FAIL'} ({latency}s) {explanation}")

    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
    passed = sum(r["grade"]["pass"] for r in rows)
    lo, hi = wilson(passed, len(rows))
    print(f"\n{args.variant}: pass {passed}/{len(rows)} = {passed / len(rows):.0%} (95% CI {lo:.0%}-{hi:.0%}), model {model}")
    for metric in ("recall", "no_wrong", "cited", "asks_info"):
        vals = [r["grade"][metric] for r in rows if metric in r["grade"]]
        if vals:
            print(f"  {metric:<10} {sum(vals) / len(vals):.0%} over {len(vals)} cases")
    by_tag = defaultdict(list)
    for r in rows:
        by_tag[r["tags"][0]].append(r["grade"]["pass"])
    print("  by type:  " + ", ".join(f"{t} {sum(v)}/{len(v)}" for t, v in by_tag.items()))


if __name__ == "__main__":
    main()
