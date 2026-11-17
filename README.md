# Unclaimed

Describe your situation, get the benefit programs you likely qualify for, what each pays, and the documents you need. Every answer is drawn only from the program documents in `docs/` and cites them.

Plan and design notes: [PLAN.md](PLAN.md).

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows; macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp
ollama pull qwen3:14b-q4_K_M   # free local model; any Ollama model works via MODEL_NAME
```

Everything runs on your machine. No API keys, no paid services.

## Run

```bash
python ingest.py               # reads docs/*.pdf, rebuilds chroma_store/
uvicorn app:app --reload       # open http://127.0.0.1:8000
```

`GET /health` returns the chunk count, so you can confirm ingest ran. `POST /ask` takes `{"question": "...", "history": [], "region": null}`.

Set each PDF's program name and region in `docs/meta.json` (see `docs/README.txt`). When the documents cover more than one region, the page shows a "Where you live" picker (`GET /regions`) and answers only from that region's programs. Your PDFs, `meta.json` and any `docs/*.jsonl` stay out of git.

## Test

```bash
pytest
```

The tests check chunking, retrieval and the eval grader. They never call the LLM.

## Eval

```bash
python evals/run_eval.py                  # 25 test people against 12 fictional programs, graded by code
python evals/run_eval.py --variant v1     # after a change; compare variants in the report
python evals/run_eval.py --real           # your own docs/*.pdf + docs/real_cases.jsonl (same case format, plus "region")
```

The cases are in [evals/REVIEW.md](evals/REVIEW.md). Results go to `evals/results/`. A case passes only if it finds every expected program, lists nothing wrong or invented, has every citation verified, and asks for missing facts when the person is vague.

## Swap points

- `rag/embed.py` `embed()`: embedding model (currently all-MiniLM-L6-v2 via Chroma's ONNX build)
- `rag/generate.py` `generate()`: LLM provider (currently local Ollama, model from `MODEL_NAME`)
- `rag/loader.py` `load_documents()`: document source
- `store.MAX_DISTANCE`: how close a chunk must be to count as relevant; tune it once real documents are loaded

Results suggest eligibility only. They don't guarantee anyone gets the benefit.
