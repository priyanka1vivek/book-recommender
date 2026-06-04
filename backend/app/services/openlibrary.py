"""
services/openlibrary.py — Integration with the Open Library API.

Open Library (openlibrary.org) is a free, open-source catalog run by the Internet Archive.
It contains metadata for over 20 million books. No API key required.

This service lets users search for any book ever published, fetch its metadata,
embed its description, and permanently add it to the local database — effectively
making the recommendation pool infinite.

API endpoints used:
  Search:    https://openlibrary.org/search.json?q=...
  Cover art: https://covers.openlibrary.org/b/id/{cover_id}-M.jpg
"""

import httpx
from sqlalchemy.orm import Session

from app.models.book import Book
from app.services.embeddings import embed_book
from app.services.recommender import add_book_embedding

# Open Library search endpoint
OL_SEARCH_URL = "https://openlibrary.org/search.json"


def _parse_ol_doc(doc: dict) -> dict | None:
    """
    Converts a raw Open Library search result document into our Book schema.
    Returns None if the result doesn't have enough data to be useful.
    """
    title = doc.get("title", "").strip()
    if not title:
        return None

    authors = doc.get("author_name", [])
    author = authors[0] if authors else "Unknown Author"

    # Build a description from whatever Open Library provides.
    # 'first_sentence' is the opening line of the book — great for embedding.
    # If missing, we fall back to a list of subjects (topics/themes).
    first_sentence = doc.get("first_sentence", None)
    if isinstance(first_sentence, dict):
        description = first_sentence.get("value", "")
    elif isinstance(first_sentence, list) and first_sentence:
        description = str(first_sentence[0])
    else:
        description = ""

    if not description:
        subjects = doc.get("subject", [])[:8]  # top 8 topics
        if subjects:
            description = f"A book covering themes of {', '.join(subjects)}."
        else:
            description = f"A book by {author}."

    # Truncate very long descriptions so embeddings stay focused
    description = description[:900]

    # Pick a genre from the first subject tag, or default to General
    subjects_list = doc.get("subject", [])
    genre = subjects_list[0] if subjects_list else "General"
    if len(genre) > 60:  # some OL subjects are very long phrases
        genre = genre[:60]

    year = doc.get("first_publish_year")

    cover_id = doc.get("cover_i")
    cover_url = (
        f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
    )

    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else None

    # The Open Library "Works" key uniquely identifies a book (not edition)
    # e.g. "/works/OL45804W"  →  we store "OL45804W"
    raw_key = doc.get("key", "")
    ol_key = raw_key.replace("/works/", "") if raw_key else None

    return {
        "title": title,
        "author": author,
        "description": description,
        "genre": genre,
        "year": year,
        "cover_url": cover_url,
        "isbn": isbn,
        "ol_key": ol_key,
    }


def search_and_import(query: str, db: Session, limit: int = 10) -> list[Book]:
    """
    Searches Open Library for 'query', imports any new books into SQLite + ChromaDB,
    and returns the full list of matching Book objects (both new and already-existing).

    This is the function that makes the app work for "almost every book ever."
    """
    params = {
        "q": query,
        # Only request the fields we actually need (faster response)
        "fields": "key,title,author_name,subject,first_publish_year,isbn,cover_i,first_sentence",
        "limit": limit,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(OL_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        raise RuntimeError("Open Library took too long to respond. Try again.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Open Library returned an error: {e.response.status_code}")

    docs = data.get("docs", [])
    imported_books: list[Book] = []

    for doc in docs:
        parsed = _parse_ol_doc(doc)
        if parsed is None:
            continue

        # --- Deduplication: skip if already in our database ---
        ol_key = parsed.get("ol_key")
        if ol_key:
            existing = db.query(Book).filter(Book.ol_key == ol_key).first()
        else:
            # Fall back to title + author match if no OL key
            existing = (
                db.query(Book)
                .filter(Book.title == parsed["title"], Book.author == parsed["author"])
                .first()
            )

        if existing:
            imported_books.append(existing)
            continue

        # --- New book: save to SQLite ---
        new_book = Book(**parsed)
        db.add(new_book)
        db.flush()  # assigns new_book.id without committing yet

        # --- Generate embedding and save to ChromaDB ---
        embedding = embed_book(
            title=new_book.title,
            author=new_book.author,
            description=new_book.description,
            genre=new_book.genre,
        )
        add_book_embedding(book_id=new_book.id, embedding=embedding, db=db)

        imported_books.append(new_book)

    db.commit()  # persist all new books at once
    return imported_books
