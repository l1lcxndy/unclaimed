import json
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import httpx  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from rag import store  # noqa: E402
from rag.generate import generate, generate_stream, mark_cited  # noqa: E402

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


def retrieve(req):
    history = [t.model_dump() for t in req.history][-6:]
    while history and history[0]["role"] != "user":
        history.pop(0)
    # Follow-ups ("what about my wife?") need earlier turns to retrieve anything; newest first
    # because the embedding model truncates long input from the end.
    earlier = [t["content"] for t in reversed(history) if t["role"] == "user"]
    chunks = store.query_many(collection, [" ".join([req.question, *earlier]), *situation_parts(req.question)],
                              region=req.region)
    return history, chunks


def sources(chunks):
    seen = dict.fromkeys((c["metadata"]["program_name"], c["metadata"]["source_file"], c["metadata"]["page"]) for c in chunks)
    return [{"program_name": p, "source_file": f, "page": pg} for p, f, pg in seen]


def model_error(e):
    """(status, message) for a failed local model call."""
    if isinstance(e, httpx.ConnectError):
        return 503, "The local model isn't running. Start Ollama, then try again."
    if isinstance(e, httpx.HTTPStatusError):
        return 502, f"The local model returned an error ({e.response.status_code}). Is MODEL_NAME pulled in Ollama?"
    return 502, f"The local model call failed ({type(e).__name__}). Try again."


@app.post("/ask")
def ask(req: AskRequest):
    history, chunks = retrieve(req)
    if not chunks:
        return {"answer": NO_MATCH, "programs": [], "sources": [], "missing_info": []}
    try:
        result = generate(req.question, chunks, history)
    except (httpx.HTTPError, ValidationError) as e:
        raise HTTPException(*model_error(e))
    return {
        "answer": result.summary,
        "programs": mark_cited(result.programs, chunks),
        "sources": sources(chunks),
        "missing_info": result.missing_info,
    }


@app.post("/ask/stream")
def ask_stream(req: AskRequest):
    """The same answer as /ask, as NDJSON events while it's worked out: start (programs being checked), checked,
    program (one card each), then done or error."""
    history, chunks = retrieve(req)

    def events():
        names = list(dict.fromkeys(c["metadata"]["program_name"] for c in chunks))
        yield {"type": "start", "checking": names, "sources": sources(chunks)}
        if not chunks:
            yield {"type": "done", "answer": NO_MATCH, "missing_info": []}
            return
        try:
            for kind, value in generate_stream(req.question, chunks, history):
                if kind == "checked":
                    yield {"type": "checked", "done": value, "of": len(names)}
                elif kind == "program":
                    yield {"type": "program", **mark_cited([value], chunks)[0]}
                else:
                    yield {"type": "done", "answer": value.summary, "missing_info": value.missing_info}
        except (httpx.HTTPError, ValidationError) as e:
            yield {"type": "error", "message": model_error(e)[1]}

    return StreamingResponse((json.dumps(e) + "\n" for e in events()), media_type="application/x-ndjson")


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent / "frontend", html=True), name="frontend")
