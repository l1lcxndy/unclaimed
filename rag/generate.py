import os
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "answer.txt").read_text(encoding="utf-8")


class RuleCheck(BaseModel):
    requirement: str
    persons_fact: str
    status: Literal["met", "not_met", "unknown"]


class ProgramMatch(BaseModel):
    program_name: str
    rule_checks: list[RuleCheck]
    benefit: str
    why_you_match: str
    documents_required: list[str]
    source_file: str
    page: int


class Answer(BaseModel):
    summary: str
    programs: list[ProgramMatch]
    missing_info: list[str]


def format_chunks(chunks):
    return "\n\n".join(
        f"[program: {c['metadata']['program_name']} | file: {c['metadata']['source_file']} | page: {c['metadata']['page']}]\n{c['text']}"
        for c in chunks
    )


def eligibility(program):
    """Verdict from the rule checks, decided in code: any failed rule rules it out, and a program
    with no rule actually met by something the person said has nothing to stand on."""
    statuses = [r.status for r in program.rule_checks]
    if "not_met" in statuses or "met" not in statuses:
        return "not_eligible"
    return "some_facts_unknown" if "unknown" in statuses else "meets_all_rules"


def mark_cited(programs, chunks):
    """Each program as a dict plus `eligibility` and `cited` (True only if its source page was actually retrieved)."""
    retrieved = {(c["metadata"]["source_file"], c["metadata"]["page"]) for c in chunks}
    return [{**p.model_dump(), "eligibility": eligibility(p), "cited": (p.source_file, p.page) in retrieved}
            for p in programs]


def generate(question, chunks, history=()):
    """Answer from retrieved chunks only, using a local Ollama model (free, nothing leaves the machine).
    history: prior {role, content} turns, starting with a user turn."""
    messages = [*history, {"role": "user", "content": PROMPT.format(question=question, chunks=format_chunks(chunks))}]
    response = httpx.post(
        f"{os.getenv('OLLAMA_URL') or 'http://127.0.0.1:11434'}/api/chat",
        json={
            "model": os.getenv("MODEL_NAME") or "qwen3:14b-q4_K_M",
            "messages": messages,
            "stream": False,
            "think": False,
            "format": Answer.model_json_schema(),
            "options": {"temperature": 0, "num_ctx": 8192},
        },
        timeout=600,
    )
    response.raise_for_status()
    answer = Answer.model_validate_json(response.json()["message"]["content"])
    answer.programs = [p for p in answer.programs if eligibility(p) != "not_eligible"]
    return answer
