"""
services/embeddings.py — Converts text into 384-dimensional embedding vectors.

We load the 'all-MiniLM-L6-v2' model directly via HuggingFace Transformers + PyTorch,
bypassing the sentence-transformers wrapper library. The math is identical — we just
implement the two steps that sentence-transformers does internally:

  1. Mean pooling:  average all token embeddings, weighted by the attention mask
  2. L2 normalise:  scale the vector so its length equals 1.0

Why implement it ourselves?
  sentence-transformers pulls in scikit-learn as a dependency, which has Cython
  extensions that don't yet have pre-built wheels for Python 3.14. By using
  transformers + torch directly, we get identical output with no compilation needed.

Interview talking point:
  "I implemented mean-pooling and L2-normalization from scratch using PyTorch —
   that's exactly what sentence-transformers does under the hood, so I cut a
   dependency and gained a deeper understanding of the pipeline."
"""

import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Module-level singletons — loaded once at first call, then cached in memory.
_tokenizer: AutoTokenizer | None = None
_model: AutoModel | None = None


def _get_model():
    """Lazy-load tokenizer and model. Downloads ~90 MB once, then uses local cache."""
    global _tokenizer, _model
    if _model is None:
        print(f"[Embeddings] Loading '{MODEL_NAME}' (first load may download ~90 MB)…")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.eval()  # disable dropout — we're doing inference, not training
        print("[Embeddings] Model ready.")
    return _tokenizer, _model


def _mean_pool(token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """
    Average all token embeddings for each sentence, ignoring padding tokens.

    The attention_mask is 1 for real tokens and 0 for padding.
    Expanding it to the embedding dimension and using it as a weight ensures
    padding tokens don't contribute to the average.
    """
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)  # avoid division by zero
    return sum_embeddings / sum_mask


def embed_text(text: str) -> list[float]:
    """
    Convert any string into a 384-float vector encoding its semantic meaning.

    The output is L2-normalized (vector length = 1.0), which means:
      cosine_similarity(a, b) == dot_product(a, b)
    This lets us use simple numpy matrix multiplication for similarity search.
    """
    tokenizer, model = _get_model()

    encoded = tokenizer(
        [text],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():  # no gradient tracking needed — saves memory and time
        output = model(**encoded)

    embedding = _mean_pool(output.last_hidden_state, encoded["attention_mask"])
    # L2 normalization: divide each vector by its Euclidean length
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

    return embedding[0].numpy().tolist()  # numpy → plain Python list for JSON compatibility


def embed_book(title: str, author: str, description: str, genre: str) -> list[float]:
    """
    Build a rich combined text before embedding.
    Including title, author, and genre gives the model more context — the embedding
    will capture all these dimensions, not just the description words.

    Example combined string:
      "Dune by Frank Herbert. Genre: Science Fiction. On the desert planet Arrakis…"
    """
    combined = f"{title} by {author}. Genre: {genre}. {description}"
    return embed_text(combined)
