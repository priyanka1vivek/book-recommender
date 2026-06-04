"""
routers/books.py — CRUD endpoints for the local book catalog.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.book import Book
from app.services.openlibrary import search_and_import

router = APIRouter(prefix="/books", tags=["Books"])


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    description: str
    genre: str
    language: Optional[str]
    year: Optional[int]
    cover_url: Optional[str]
    isbn: Optional[str]
    ol_key: Optional[str]

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[BookOut], summary="List all books in the local database")
def list_books(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    genre: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None, description="Filter by language: English, Hindi, Kannada"),
    db: Session = Depends(get_db),
):
    q = db.query(Book)
    if genre:
        q = q.filter(Book.genre.ilike(f"%{genre}%"))
    if language:
        q = q.filter(Book.language.ilike(language))
    return q.order_by(Book.title).offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")
    return book


@router.get("/discover", response_model=list[BookOut], summary="Search Open Library and import new books")
def discover_books(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, le=20),
    db: Session = Depends(get_db),
):
    try:
        books = search_and_import(query=q, db=db, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not books:
        raise HTTPException(status_code=404, detail="No books found for that query.")
    return books
