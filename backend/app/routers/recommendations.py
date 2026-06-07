"""
routers/recommendations.py — POST /recommend/vibe

The star endpoint. Accepts a free-form vibe description and an optional language
filter, embeds the query with BERT, and returns the k closest books by cosine
similarity.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.models.book import Book
from app.services.embeddings import embed_text
from app.services.recommender import query_similar_books

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


class VibeRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="A mood, feeling, or vibe description.",
        examples=["dark rainy detective story", "cozy autumn fantasy"],
    )
    k: int = Field(default=5, ge=1, le=20)
    # None = no filter (search all languages)
    language: Optional[str] = Field(
        default=None,
        description="Filter by language: 'English', 'Hindi', 'Kannada', or null for all.",
    )


class BookRecommendation(BaseModel):
    id: int
    title: str
    author: str
    description: str
    genre: str
    language: Optional[str]
    year: Optional[int]
    cover_url: Optional[str]
    similarity_score: float

    model_config = {"from_attributes": True}


@router.post("/vibe", response_model=list[BookRecommendation])
def vibe_check(request: VibeRequest, db: Session = Depends(get_db)):
    """
    Convert the query string into a BERT embedding, then find the k most similar
    book embeddings using numpy cosine similarity.

    Language filter:
      When language is provided, only books in that language are searched.
      If no books match (e.g. Kannada library is empty), returns an empty list
      rather than falling back to English — the frontend handles this gracefully.
    """
    query_embedding = embed_text(request.query)

    similar = query_similar_books(
        query_embedding,
        db=db,
        k=request.k,
        language=request.language,
    )

    results: list[BookRecommendation] = []
    for match in similar:
        book = db.query(Book).filter(Book.id == match["book_id"]).first()
        if book:
            results.append(
                BookRecommendation(
                    id=book.id,
                    title=book.title,
                    author=book.author,
                    description=book.description,
                    genre=book.genre,
                    language=book.language,
                    year=book.year,
                    cover_url=book.cover_url,
                    similarity_score=match["similarity_score"],
                )
            )
    return results
