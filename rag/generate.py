import difflib
import json
import os
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "answer.txt").read_text(encoding="utf-8")


class Requirement(BaseModel):
    requirement: str
    persons_fact: str
    person_fits: Literal["yes", "no", "unknown"]


class GroupCheck(BaseModel):
    group: str
    persons_fact: str
    person_is_in_group: Literal["yes", "no", "unknown"]


class TargetGroup(BaseModel):
    group: str
    household_member: str
    persons_fact: str
    member_is_in_group: Literal["yes", "no", "unknown"]


class ProgramMatch(BaseModel):
    program_name: str
    who_its_for: TargetGroup
    who_can_apply: list[Requirement]
    who_cannot_apply: list[GroupCheck]
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
    """Verdict from the rule checks, decided in code: the person must be in the group the program is for,
    and a failed requirement or a matching exclusion rules it out. Unknown paperwork rules don't."""
    fits = [r.person_fits for r in program.who_can_apply]
    excluded = [e.person_is_in_group for e in program.who_cannot_apply]
    if program.who_its_for.member_is_in_group != "yes" or "no" in fits or "yes" in excluded:
        return "not_eligible"
    return "some_facts_unknown" if "unknown" in fits + excluded else "meets_all_rules"


def match_names(programs, chunks):
    """Rename each program to the retrieved program it means ("WIC Program" -> "WIC"). Programs matching nothing
    retrieved, or repeating one already listed, are dropped."""
    names = sorted({c["metadata"]["program_name"] for c in chunks}, key=len, reverse=True)
    lower = {n.lower(): n for n in names}
    kept = {}
    for p in programs:
        said = p.program_name.lower()
        name = (lower.get(said)
                or next((n for n in names if n.lower() in said or said in n.lower()), None)
                or next(iter(difflib.get_close_matches(said, lower, n=1, cutoff=0.6)), None))
        name = lower.get(name, name)
        if name and name not in kept:
            kept[name] = p.model_copy(update={"program_name": name})
    return list(kept.values())


def mark_cited(programs, chunks):
    """Each program as a dict plus `eligibility` and `cited` (True only if its source page was actually retrieved)."""
    retrieved = {(c["metadata"]["source_file"], c["metadata"]["page"]) for c in chunks}
    return [{**p.model_dump(), "eligibility": eligibility(p), "cited": (p.source_file, p.page) in retrieved}
            for p in programs]


def complete_programs(text):
    """The program objects already closed in a partial `{"summary": ..., "programs": [{...}, {...` reply."""
    start = text.find('"programs"')
    start = text.find("[", start) if start >= 0 else -1
    if start < 0:
        return []
    found, depth, in_string, escaped, obj_start = [], 0, False, False, None
    for i in range(start + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
            obj_start = i if depth == 1 else obj_start
        elif ch == "}":
            depth -= 1
            if depth == 0:
                found.append(json.loads(text[obj_start:i + 1]))
        elif ch == "]" and depth == 0:
            break
    return found


def generate_stream(question, chunks, history=()):
    """Answer from retrieved chunks only, using a local Ollama model (free, nothing leaves the machine).
    Yields ("checked", n) after each program is checked, ("program", ProgramMatch) for each one the person may
    qualify for, then ("answer", Answer). history: prior {role, content} turns, starting with a user turn."""
    messages = [*history, {"role": "user", "content": PROMPT.format(question=question, chunks=format_chunks(chunks))}]
    body = {
        "model": os.getenv("MODEL_NAME") or "qwen3:14b-q4_K_M",
        "messages": messages,
        "stream": True,
        "think": False,
        "format": Answer.model_json_schema(),
        "options": {"temperature": 0, "num_ctx": 8192},
    }
    text, checked, kept = "", 0, {}
    with httpx.stream("POST", f"{os.getenv('OLLAMA_URL') or 'http://127.0.0.1:11434'}/api/chat", json=body,
                      timeout=600) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            piece = json.loads(line).get("message", {}).get("content", "")
            text += piece
            if "}" not in piece:
                continue
            for raw in complete_programs(text)[checked:]:
                checked += 1
                yield "checked", checked
                program = ProgramMatch.model_validate(raw)
                if eligibility(program) == "not_eligible":
                    continue
                for named in match_names([program], chunks):
                    if named.program_name not in kept:
                        kept[named.program_name] = named
                        yield "program", named
    answer = Answer.model_validate_json(text)
    answer.programs = list(kept.values())
    yield "answer", answer


def generate(question, chunks, history=()):
    """The whole answer at once (see generate_stream)."""
    return next(value for kind, value in generate_stream(question, chunks, history) if kind == "answer")
