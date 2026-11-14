from pathlib import Path

import chromadb

from rag.embed import embed

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "chroma_store"
COLLECTION = "programs"
MAX_DISTANCE = 0.75


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


def query_many(collection, texts, k=8, max_distance=MAX_DISTANCE, limit=10):
    """Search several texts at once and merge. Every text's best hits come first, so one strong need
    ("rideshare driver") can't crowd out another ("kid aged 3")."""
    count = collection.count()
    if count == 0:
        return []
    result = collection.query(query_embeddings=embed(texts), n_results=min(k, count))
    best = {}
    for ids, docs, metas, dists in zip(result["ids"], result["documents"], result["metadatas"], result["distances"]):
        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            if dist > max_distance:
                continue
            seen = best.get(cid)
            if seen is None or (rank, dist) < (seen["rank"], seen["distance"]):
                best[cid] = {"text": doc, "metadata": meta, "distance": dist, "rank": rank}
    hits = sorted(best.values(), key=lambda c: (c["rank"], c["distance"]))[:limit]
    return [{k: v for k, v in c.items() if k != "rank"} for c in hits]
