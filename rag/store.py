from collections import Counter
from pathlib import Path

import chromadb

from rag.embed import embed

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "chroma_store"
COLLECTION = "programs"
MAX_DISTANCE = 0.85
ELIGIBILITY = "Am I eligible? Who can get this and what are the requirements to qualify"
LONG_DOC_CHUNKS = 10


def get_collection(path=None, reset=False):
    client = chromadb.PersistentClient(path=str(path or DEFAULT_PATH))
    if reset and COLLECTION in [c if isinstance(c, str) else c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def add(collection, chunks, batch=256):
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        texts = [c["text"] for c in part]
        collection.add(
            ids=[c["id"] for c in part],
            documents=texts,
            metadatas=[c["metadata"] for c in part],
            embeddings=embed(texts),
        )


def query(collection, text, k=5, max_distance=MAX_DISTANCE):
    return query_many(collection, [text], k=k, max_distance=max_distance)


def regions(collection):
    return sorted({m["region"] for m in collection.get(include=["metadatas"])["metadatas"]})


def query_many(collection, texts, k=8, max_distance=MAX_DISTANCE, limit=10, region=None):
    """Search several texts at once and merge. Every text's best hits come first, so one strong need
    ("rideshare driver") can't crowd out another ("kid aged 3"). A long document's second slot goes to its passage
    that best says who qualifies, so its tables and examples can't push out its rules.
    region limits results to one region's programs."""
    count = collection.count()
    if count == 0:
        return []
    result = collection.query(query_embeddings=embed(texts), n_results=min(k, count),
                              where={"region": region} if region else None)
    best = {}
    for ids, docs, metas, dists in zip(result["ids"], result["documents"], result["metadatas"], result["distances"]):
        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            if dist > max_distance:
                continue
            seen = best.get(cid)
            if seen is None or (rank, dist) < (seen["rank"], seen["distance"]):
                best[cid] = {"text": doc, "metadata": meta, "distance": dist, "rank": rank}
    hits = sorted(best.values(), key=lambda c: (c["rank"], c["distance"]))
    nth = Counter()
    for c in hits:
        c["nth"] = nth[c["metadata"]["program_name"]]
        nth[c["metadata"]["program_name"]] += 1
    for name in nth:
        if len(collection.get(where={"program_name": name}, include=[])["ids"]) <= LONG_DOC_CHUNKS:
            continue
        r = collection.query(query_embeddings=embed([ELIGIBILITY]), n_results=1, where={"program_name": name})
        rule = best.get(r["ids"][0][0])
        if rule:
            if rule["nth"] <= 1:
                continue
            hits.remove(rule)
        for c in hits:
            if c["metadata"]["program_name"] == name and c["nth"] >= 1:
                c["nth"] += 1
        hits.append({"text": r["documents"][0][0], "metadata": r["metadatas"][0][0],
                     "distance": r["distances"][0][0], "nth": 1})
    hits = sorted(hits, key=lambda c: c["nth"])[:limit]
    return [{k: v for k, v in c.items() if k not in ("rank", "nth")} for c in hits]
