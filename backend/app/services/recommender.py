"""
services/recommender.py — numpy-based cosine similarity over SQLite-stored embeddings.

Why numpy instead of a dedicated vector database (ChromaDB, Pinecone, Qdrant)?
  - chroma-hnswlib has no pre-built wheel for Python 3.14 yet
  - numpy ships a cp314 binary wheel and is already installed
  - For up to ~50,000 books the matrix-vector multiply runs in <5 ms on CPU
  - The math is transparent and easy to explain: one line of numpy code

The cosine similarity shortcut:
  All embeddings are L2-normalised (vector length = 1.0) by the embedding service.
  For unit vectors:  cosine_similarity(a, b) = dot_product(a, b)
  So:  all_scores = embedding_matrix @ query_vector  (one matrix multiply = all similarities)
"""

import json
import numpy as np
from sqlalchemy.orm import Session
from app.models.book import Book


def add_book_embedding(book_id: int, embedding: list[float], db: Session) -> None:
    """
    Persist a book's embedding into the SQLite books table as a JSON string.
    The caller is responsible for calling db.commit() after all upserts are done.

    Why JSON instead of a BLOB?
      JSON is human-readable (you can inspect the DB with any SQLite viewer),
      trivially deserialised by json.loads(), and numpy can consume the resulting
      Python list directly. The overhead vs BLOB is negligible for 384 floats.
    """
    db.query(Book).filter(Book.id == book_id).update(
        {"embedding_json": json.dumps(embedding)}
    )


def query_similar_books(
    query_embedding: list[float],
    db: Session,
    k: int = 5,
    language: str | None = None,
) -> list[dict]:
    """
    Find the k most semantically similar books to query_embedding.

    Args:
        query_embedding: 384-float L2-normalised query vector.
        db:              SQLAlchemy session (injected by FastAPI Depends).
        k:               How many results to return.
        language:        Optional language filter ('Hindi', 'Kannada', 'English').
                         None = search across all languages.

    Returns:
        List of {"book_id": int, "similarity_score": float}, sorted best-first.

    Performance note:
        Loading and multiplying a (N × 384) float32 matrix is O(N·384) which is
        ~15 MB RAM and <5 ms for N = 10,000 on a modern CPU.
        A production system with millions of entries would use an ANN index
        (FAISS, HNSW) instead — but for a local demo this is instant.
    """
    # Build the SQLAlchemy query — only retrieve books that have been embedded.
    # Optionally narrow to a specific language.
    q = db.query(Book).filter(Book.embedding_json.isnot(None))
    if language:
        # Case-insensitive match so "hindi" and "Hindi" both work
        q = q.filter(Book.language.ilike(language))
    books = q.all()

    if not books:
        return []

    # Stack all embeddings into a 2-D numpy array: shape (N, 384)
    # dtype=float32 halves memory vs float64 with negligible precision loss
    matrix = np.array(
        [json.loads(b.embedding_json) for b in books], dtype=np.float32
    )

    # Query vector: shape (384,)
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Matrix-vector multiply → shape (N,)
    # Each element is the cosine similarity between the query and that book's embedding.
    similarities = matrix @ query_vec

    # Clamp k to available books (can't return more than we have)
    n = min(k, len(books))
    # argsort returns indices sorted ascending; [::-1] reverses to descending
    top_indices = np.argsort(similarities)[::-1][:n]

    return [
        {
            "book_id": books[int(idx)].id,
            "similarity_score": round(float(similarities[idx]), 4),
        }
        for idx in top_indices
    ]


def reset_embeddings(db: Session) -> None:
    """Wipe all stored embeddings. Used by seed.py for a clean rebuild."""
    updated = db.query(Book).update({"embedding_json": None})
    db.commit()
    if updated:
        print(f"[Recommender] Cleared embeddings for {updated} books.")
