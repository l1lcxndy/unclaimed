"""Rebuild the vector store from docs/*.pdf. Optional docs/meta.json overrides per-file metadata:
{"some-program.pdf": {"program_name": "...", "region": "...", "category": "..."}}"""
import json
from pathlib import Path

from rag import store
from rag.chunker import chunk_text
from rag.loader import load_documents

DOCS = Path(__file__).resolve().parent / "docs"


def build_chunks(docs_dir):
    meta_file = docs_dir / "meta.json"
    overrides = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    chunks = []
    for name, page, text in load_documents(docs_dir):
        stem = Path(name).stem
        info = overrides.get(name, {})
        for i, piece in enumerate(chunk_text(text)):
            chunks.append({
                "id": f"{stem}_p{page}_c{i}",
                "text": piece,
                "metadata": {
                    "program_name": info.get("program_name", stem.replace("-", " ").replace("_", " ").title()),
                    "source_file": name,
                    "page": page,
                    "region": info.get("region", "national"),
                    "category": info.get("category", "general"),
                },
            })
    return chunks


def main():
    chunks = build_chunks(DOCS)
    if not chunks:
        raise SystemExit(f"No text found in {DOCS}\\*.pdf. Add text-based PDFs and run again.")
    collection = store.get_collection(reset=True)
    store.add(collection, chunks)
    print(f"Ingested {len(chunks)} chunks from {DOCS}.")


if __name__ == "__main__":
    main()
