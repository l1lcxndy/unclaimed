from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# all-MiniLM-L6-v2 via ONNX: same model as sentence-transformers, without the torch install
_model = DefaultEmbeddingFunction()


def embed(texts):
    return [[float(x) for x in vector] for vector in _model(list(texts))]
