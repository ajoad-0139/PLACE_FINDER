from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_model():
    from fastembed import TextEmbedding
    return TextEmbedding(settings.EMBEDDING_MODEL)


def embed_texts(texts):
    """List of strings -> list of 384-dim float lists."""
    return [vec.tolist() for vec in get_model().embed(list(texts))]


def embed_text(text):
    """One string -> one 384-dim float list."""
    return embed_texts([text])[0]