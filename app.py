import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import httpx  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from rag import store  # noqa: E402
from rag.generate import generate, mark_cited  # noqa: E402

NO_MATCH = (
    "I couldn't find any program documents that match this situation. "
    "Try adding details like age, work, income, family or where you live."
)

app = FastAPI(title="Unclaimed")
collection = store.get_collection()


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = Field(default=[], max_length=20)
    region: str | None = Field(default=None, max_length=100)


def situation_parts(text):
    """'driver, married, one kid aged 3' -> separate searches, one per need. One-word parts are too vague to search."""
    parts = (p.strip() for p in re.split(r"[.,;!?\n]+|\band\b|\bbut\b", text))
    return [p for p in parts if len(p.split()) >= 2][:6]


@app.get("/health")
def health():
    return {"ok": True, "chunks": collection.count()}


@app.get("/regions")
def regions():
    return store.regions(collection)


@app.post("/ask")
def ask(req: AskRequest):
    history = [t.model_dump() for t in req.history][-6:]
    while history and history[0]["role"] != "user":
        history.pop(0)
    # Follow-ups ("what about my wife?") need earlier turns to retrieve anything; newest first
    # because the embedding model truncates long input from the end.
    earlier = [t["content"] for t in reversed(history) if t["role"] == "user"]
    chunks = store.query_many(collection, [" ".join([req.question, *earlier]), *situation_parts(req.question)],
                              region=req.region)
    if not chunks:
        return {"answer": NO_MATCH, "programs": [], "sources": [], "missing_info": []}

    try:
        result = generate(req.question, chunks, history)
    except httpx.ConnectError:
        raise HTTPException(503, "The local model isn't running. Start Ollama, then try again.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"The local model returned an error ({e.response.status_code}). Is MODEL_NAME pulled in Ollama?")
    except (httpx.HTTPError, ValidationError) as e:
        raise HTTPException(502, f"The local model call failed ({type(e).__name__}). Try again.")

    seen = dict.fromkeys((c["metadata"]["program_name"], c["metadata"]["source_file"], c["metadata"]["page"]) for c in chunks)
    return {
        "answer": result.summary,
        "programs": mark_cited(result.programs, chunks),
        "sources": [{"program_name": p, "source_file": f, "page": pg} for p, f, pg in seen],
        "missing_info": result.missing_info,
    }


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent / "frontend", html=True), name="frontend")
