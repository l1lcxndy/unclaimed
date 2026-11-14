CHUNK_CHARS = 2400  # ~600 tokens
OVERLAP_CHARS = 400  # ~100 tokens


def chunk_text(text, size=CHUNK_CHARS, overlap=OVERLAP_CHARS):
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start + size - overlap, end)
            if cut > start:
                end = cut
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
