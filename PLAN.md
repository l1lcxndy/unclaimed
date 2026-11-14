# Unclaimed — Benefit Eligibility Assistant

A retrieval-augmented assistant that reads government benefit-program documents and tells a person exactly which programs they qualify for, the benefit amount, and the documents they're missing to claim it — with every answer cited back to the source document.

RAG engine first, program data second. Swap the document set and the same engine serves any domain (insurance policies, legal rights, internal company docs, college rules).

---

## 1. Problem

Thousands of national and regional benefit programs exist. Most eligible people never claim them because the eligibility rules and document requirements are buried in bureaucratic PDFs and scattered portals. The information exists; it is unreadable and un-navigable for the people it's meant for.

## 2. User

One of:
- A gig worker / farmer / small shopkeeper checking what they're owed.
- A volunteer or nonprofit field worker helping several such people.

Not "citizens" in the abstract. One person trying to get money the government already set aside for them.

## 3. What it does

- Takes a plain-language description of a person's situation ("24-year-old rideshare driver, married, one child").
- Returns the programs they likely qualify for, each with: program name, benefit (amount / entitlement), eligibility match, and the exact documents required to claim.
- Cites the source program document for every claim it makes, so answers are grounded, not invented.
- Flags what information is still missing to decide eligibility ("need: annual income, land ownership").
- Handles follow-up questions in the same conversation ("what about my wife?").

---

## 4. Architecture

Three stages. Every RAG system is these three.

```
INGEST (one-time, offline)
  program PDFs ──► extract text ──► chunk ──► embed ──► store vectors + metadata
                                                         (ChromaDB)

QUERY (per request)
  user question ──► embed ──► similarity search in ChromaDB ──► top-k chunks
        │                                                          │
        └──────────────────────────┬───────────────────────────────┘
                                    ▼
                         prompt = question + retrieved chunks
                                    ▼
                               LLM generates
                                    ▼
                     answer + cited source chunks  ──►  user
```

- **Ingest** is a script you run when documents change. Output lives in a local Chroma store committed/gitignored as you prefer.
- **Query** is the live path: embed → retrieve → generate. No model training, ever.
- **Grounding rule:** the LLM is instructed to answer *only* from retrieved chunks and to name the program each fact came from. If nothing relevant is retrieved, it says so instead of guessing.

---

## 5. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Your strongest, best RAG ecosystem |
| API | FastAPI + Uvicorn | One clean async endpoint, auto docs |
| Vector store | ChromaDB (local, persistent) | Zero infra, free, runs on your machine |
| Embeddings | `sentence-transformers` → `all-MiniLM-L6-v2` | Runs local, free, fast, good enough |
| PDF parsing | `pypdf` (or `pdfplumber` for messy layouts) | Text extraction |
| Chunking | `langchain-text-splitters` (RecursiveCharacterTextSplitter) or hand-rolled | Standard, swappable |
| LLM | Pluggable: hosted API or local via Ollama | Keep it behind one function so you can swap |
| Frontend | Plain HTML + JS chat, or React if you want it to look like a product | Demo-grade UI |

Swap points, kept behind single functions so nothing else changes:
- `embed(text)` — change the embedding model here.
- `generate(question, chunks)` — change the LLM provider here.
- `load_documents(path)` — change the document source here (this is your re-skin point).

---

## 6. Repo structure

```
unclaimed/
├── README.md
├── requirements.txt
├── .env.example            # OLLAMA_URL, MODEL_NAME
├── .gitignore              # venv, .env, chroma_store/, __pycache__
├── docs/                   # source program PDFs
├── chroma_store/           # generated vector DB (gitignore or commit, your call)
├── ingest.py               # PDF → chunks → embeddings → Chroma
├── app.py                  # FastAPI app, /ask endpoint
├── rag/
│   ├── __init__.py
│   ├── loader.py           # load_documents, extract text
│   ├── chunker.py          # split text into chunks
│   ├── store.py            # Chroma client, add + query
│   ├── embed.py            # embed(text)
│   └── generate.py         # generate(question, chunks) → answer + citations
├── prompts/
│   └── answer.txt          # the grounding prompt template
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── tests/
    └── test_retrieval.py   # does a known question pull the right chunk?
```

---

## 7. Data model

Each stored chunk carries metadata so answers can cite and filter:

```json
{
  "id": "farm-income-support_chunk_014",
  "text": "Beneficiaries ... income support of 6000 per year ...",
  "metadata": {
    "program_name": "Farm Income Support",
    "source_file": "farm-income-support.pdf",
    "page": 2,
    "region": "national",
    "category": "agriculture"
  }
}
```

Metadata lets you (a) cite program + page in the answer, and (b) later filter retrieval by region or category.

---

## 8. API

**`POST /ask`**
```json
// request
{ "question": "24 year old rideshare driver, married, one kid",
  "history": [] }

// response
{
  "answer": "You likely qualify for 3 programs ...",
  "sources": [
    { "program_name": "...", "source_file": "...", "page": 2 }
  ],
  "missing_info": ["annual income", "household size"]
}
```

**`GET /health`** — returns ok + chunk count in the store (proves ingest ran).

---

## 9. The grounding prompt (the part that makes or breaks it)

Stored in `prompts/answer.txt`, roughly:

```
You are a benefits eligibility assistant.
Use ONLY the program excerpts provided below. Do not use outside knowledge.
For each program the person may qualify for, state: program name, the benefit,
why they match, and the documents required to claim.
Cite the program name for every claim. If the excerpts don't cover something,
say what information is missing. Never invent a program or a number.

PERSON'S SITUATION:
{question}

PROGRAM EXCERPTS:
{chunks}
```

The whole credibility of the project rides on this prompt + good retrieval. A judge testing "did you build something real" is really testing whether the citations hold.

---

## 10. Setup & run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # local model settings, no keys needed
# drop program PDFs into docs/
python ingest.py                # builds chroma_store/
uvicorn app:app --reload        # serves /ask
# open frontend/index.html (or serve it) and ask
```

---

## 11. Re-skin map (why this is the reusable foundation)

Change only `docs/` + the prompt's domain line, and the same engine becomes:

| Load these docs | And it becomes |
|---|---|
| Insurance policy wordings | "Will my claim get rejected?" assistant (fintech/health theme) |
| Statutes / tenancy law | Legal-rights assistant |
| A company's internal wiki/PDFs | Internal-docs assistant (any B2B theme) |
| College regulations, syllabi | Student-rules bot |
| Product manuals | Support assistant |

One engine, five hackathon themes. That is the point of building this one first.

---

## 12. Known gotchas

- **Bad PDF extraction** wrecks retrieval. Scanned/image PDFs need OCR (`pytesseract`) — prefer text PDFs for the first set.
- **Chunk size** matters: too big = noisy retrieval, too small = lost context. Start ~500–800 tokens with ~100 overlap, tune by testing.
- **Retrieval quality beats model size.** If answers are wrong, the fix is almost always better chunks/retrieval, not a bigger LLM.
- **Don't claim legal/financial certainty.** It suggests eligibility and points to official sources; it doesn't guarantee entitlement. Say that in the UI.

---

## 13. Possible extensions (pick responsibly, not all)

- Local-language input and output (voice in, voice out) — this is Foundation #5 bolted on.
- Metadata filters (retrieve only one region + agriculture programs).
- Document checklist export (PDF the person can carry to the office).
- WhatsApp interface instead of web.
- Auto-ingest from official government portals on a schedule.
- Confidence score per program match.
