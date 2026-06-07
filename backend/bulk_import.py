"""
bulk_import.py
==============
Fetches books from the Open Library API in bulk, embeds them with BERT,
and stores them in the local SQLite database.

WHY OPEN LIBRARY OVER KAGGLE:
  - No account, no API key, no manual download
  - 20 million+ books spanning every language
  - Already integrated in openlibrary.py service
  - Live data -- descriptions, covers, subjects are always current
  - Kaggle's popular GoodReads datasets have ISBNs and ratings but most
    are MISSING descriptions, which means no embeddings, which means the
    entire AI recommendation feature cannot work

HOW IT WORKS:
  1. Fetch books from Open Library in pages of 100 (the API maximum)
  2. Skip books already in the database (checked by Open Library key)
  3. Build an English description for every book regardless of language
     (so the English BERT model always gets useful text to embed)
  4. Batch-embed groups of 32 books at once (7-8x faster than one-at-a-time)
  5. Save to SQLite in one commit per batch

USAGE:
  cd backend
  python bulk_import.py                       # default: all modes
  python bulk_import.py --mode english        # English books only
  python bulk_import.py --mode hindi          # Hindi books only
  python bulk_import.py --mode kannada        # Kannada books only
  python bulk_import.py --mode english --limit 200  # cap at 200 new books
"""

import sys
import os
import time
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import httpx
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.models.book import Book
from app.services.embeddings import embed_books_batch

# ---------------------------------------------------------------------------
# Open Library API helpers
# ---------------------------------------------------------------------------
OL_SEARCH = "https://openlibrary.org/search.json"

# Fields we need -- requesting only these keeps the response small and fast.
OL_FIELDS = "key,title,author_name,subject,first_publish_year,isbn,cover_i,first_sentence,language"


def _build_description(doc: dict) -> str:
    """
    Build an English description from whatever Open Library provides.

    Priority order:
      1. first_sentence -- the opening line of the book (most specific)
      2. subjects        -- a sentence listing the book's topics
      3. generic         -- "A book by {author} about {title}"

    For Hindi/Kannada books, first_sentence is often in the original script.
    We detect this by checking if >20% of characters are non-ASCII (i.e. the
    BERT model, which was trained on English, would get poor signal from it).
    In that case we fall back to the English subjects list.

    WHY BOTHER WITH ENGLISH DESCRIPTIONS FOR NON-ENGLISH BOOKS:
      Our embedding model (all-MiniLM-L6-v2) was trained on English text.
      Feeding it Hindi script produces low-quality embeddings -- the semantic
      matching barely works. An English description like "A Hindi novel about
      rural poverty and caste oppression by Premchand" gives the model rich
      context to work with, so searches like "rural poverty India" correctly
      surface Godan even though Godan is written in Hindi.
    """
    title   = doc.get("title", "Unknown")
    authors = doc.get("author_name", [])
    author  = authors[0] if authors else "Unknown Author"

    # --- Try first_sentence ---
    raw = doc.get("first_sentence")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    elif isinstance(raw, list) and raw:
        raw = str(raw[0])
    else:
        raw = ""

    if raw:
        non_ascii = sum(1 for c in raw if ord(c) > 127)
        ascii_ratio = non_ascii / max(len(raw), 1)
        # If the text is predominantly non-ASCII (Hindi/Kannada script),
        # skip it and fall back to subjects
        if ascii_ratio < 0.3:
            return raw[:800]

    # --- Fall back to subjects ---
    subjects = doc.get("subject", [])
    if subjects:
        # Take up to 8 of the most concise subjects (skip very long ones)
        clean = [s for s in subjects if len(s) < 40][:8]
        if clean:
            return f"A book by {author} covering themes of: {', '.join(clean)}."

    # --- Generic last resort ---
    return f"'{title}' by {author}."


def _parse_ol_doc(doc: dict, default_language: str = "English") -> dict | None:
    """
    Convert a raw Open Library search result into our Book schema dict.
    Returns None if the result is too incomplete to be useful.
    """
    title = (doc.get("title") or "").strip()
    if not title:
        return None

    authors = doc.get("author_name") or []
    author  = authors[0] if authors else "Unknown Author"

    description = _build_description(doc)
    if not description or description.startswith("'") and len(description) < 30:
        return None   # too sparse to produce a meaningful embedding

    subjects = doc.get("subject") or []
    genre    = subjects[0] if subjects else "General"
    if len(genre) > 60:
        genre = genre[:60]

    isbn_list = doc.get("isbn") or []
    isbn      = isbn_list[0] if isbn_list else None

    cover_id  = doc.get("cover_i")
    cover_url = (
        f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
        if cover_id else None
    )

    raw_key = doc.get("key", "")
    ol_key  = raw_key.replace("/works/", "") if raw_key else None

    year = doc.get("first_publish_year")

    # Detect language from the doc's language field if present;
    # otherwise use the default_language passed by the caller.
    doc_langs = doc.get("language") or []
    lang_map  = {"hin": "Hindi", "kan": "Kannada", "eng": "English"}
    language  = default_language
    for code in doc_langs:
        if code in lang_map:
            language = lang_map[code]
            break

    return {
        "title":       title,
        "author":      author,
        "description": description[:900],
        "genre":       genre,
        "language":    language,
        "year":        year,
        "cover_url":   cover_url,
        "isbn":        isbn,
        "ol_key":      ol_key,
    }


def _fetch_page(
    subject:   str | None = None,
    language:  str | None = None,
    query:     str | None = None,
    limit:     int = 100,
    offset:    int = 0,
) -> list[dict]:
    """
    One page from the Open Library search API.

    WHY LIMIT=100: The API maximum per request is 100. Fetching in pages of
    100 minimises the number of HTTP round-trips while staying within limits.

    RATE LIMITING: We add a 0.4s sleep between pages. Open Library is a
    free public service -- being a courteous API consumer keeps it healthy
    for everyone.
    """
    params: dict = {
        "fields": OL_FIELDS,
        "limit":  limit,
        "offset": offset,
    }
    if query:
        params["q"] = query
    if subject:
        params["subject"] = subject
    if language:
        params["language"] = language

    try:
        resp = httpx.get(OL_SEARCH, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("docs", [])
    except Exception as e:
        print(f"\n  [warn] API error at offset {offset}: {e}")
        return []


# ---------------------------------------------------------------------------
# Import strategies per language
# ---------------------------------------------------------------------------

# English: paginate through high-quality genre subjects.
# We use multiple subjects to ensure diverse coverage rather than
# fetching 1000 mystery books and nothing else.
ENGLISH_SUBJECTS = [
    ("detective mystery crime",         80),
    ("science fiction space exploration",80),
    ("fantasy magic adventure",         80),
    ("historical fiction",              80),
    ("romance love relationship",       60),
    ("horror supernatural thriller",    60),
    ("literary fiction novel",          60),
    ("coming of age young adult",       50),
    ("biography memoir",                50),
    ("philosophy meaning of life",      50),
    ("magical realism",                 40),
    ("dystopian future society",        40),
    ("war military history novel",      40),
    ("mythology folklore",              30),
    ("travel adventure exploration",    30),
]
# Total target: ~830 English books (on top of the 30 already seeded)

# Hindi: Open Library's language= filter returns no results in practice.
# Instead we search by subject/query and filter returned books by their
# language metadata -- this surfaces real Hindi books that have English descriptions.
HINDI_QUERIES = [
    ("hindi novel fiction literature",          40),
    ("hindi classic novel premchand",           30),
    ("hindi poetry literature",                 25),
    ("Indian literature hindi fiction",         30),
    ("hindi modern fiction novel",              25),
    ("premchand hindi",                         20),
    ("bhisham sahni tamas hindi",               15),
    ("harivansh rai bachchan poetry",           15),
]

KANNADA_QUERIES = [
    ("kannada novel fiction literature",        30),
    ("kannada literature modern fiction",       25),
    ("S L Bhyrappa kannada novel",              20),
    ("Kuvempu kannada literature poetry",       20),
    ("U R Ananthamurthy kannada",               15),
    ("Poornachandra Tejaswi kannada",           15),
    ("Karnataka literature fiction",            25),
]


# ---------------------------------------------------------------------------
# Core import function
# ---------------------------------------------------------------------------

def import_books(
    db:           Session,
    docs:         list[dict],
    default_lang: str,
    seen_ol_keys: set[str],
) -> tuple[list[Book], int]:
    """
    Parse a list of raw Open Library docs, skip duplicates,
    and return new Book objects ready to be embedded.

    Returns (new_books, skipped_count)
    """
    new_books: list[Book] = []
    skipped   = 0

    for doc in docs:
        parsed = _parse_ol_doc(doc, default_language=default_lang)
        if parsed is None:
            skipped += 1
            continue

        ol_key = parsed.get("ol_key")

        # Skip if this OL key is already in the DB or seen in this run
        if ol_key and ol_key in seen_ol_keys:
            skipped += 1
            continue

        # Also check title+author for books without an OL key
        if not ol_key:
            exists = (
                db.query(Book)
                .filter(Book.title == parsed["title"], Book.author == parsed["author"])
                .first()
            )
            if exists:
                skipped += 1
                continue

        book = Book(**parsed)
        new_books.append(book)
        if ol_key:
            seen_ol_keys.add(ol_key)

    return new_books, skipped


def embed_and_save(db: Session, books: list[Book], batch_size: int = 32) -> None:
    """
    Batch-embed a list of Book objects and save their embedding_json to SQLite.

    WHY BATCH EMBEDDING:
      PyTorch's forward pass has a fixed overhead per call regardless of
      batch size (loading weights, allocating GPU tensors, etc.).
      Processing 32 texts in one call is ~8x faster than 32 individual calls
      because the overhead is paid once per batch, not once per book.
    """
    book_dicts = [
        {"title": b.title, "author": b.author, "description": b.description, "genre": b.genre}
        for b in books
    ]
    embeddings = embed_books_batch(book_dicts, batch_size=batch_size)
    for book, emb in zip(books, embeddings):
        book.embedding_json = json.dumps(emb)
    db.commit()


# ---------------------------------------------------------------------------
# Per-language import flows
# ---------------------------------------------------------------------------

def run_english(db: Session, seen_keys: set[str], per_subject_limit: int | None) -> int:
    """Fetch English books across diverse genre subjects."""
    total_added = 0
    print("\n[English] Importing across 15 genre subjects...")

    for subject, target in ENGLISH_SUBJECTS:
        limit  = per_subject_limit if per_subject_limit else target
        added  = 0
        offset = 0
        print(f"  Subject: '{subject}' (target {limit})")

        while added < limit:
            fetch_n = min(100, limit - added)
            docs    = _fetch_page(subject=subject, limit=fetch_n, offset=offset)
            if not docs:
                break

            new_books, skipped = import_books(db, docs, "English", seen_keys)

            if new_books:
                db.add_all(new_books)
                db.flush()  # get IDs
                embed_and_save(db, new_books)
                added       += len(new_books)
                total_added += len(new_books)

            bar = "#" * min(added, limit) + "." * max(0, limit - added)
            print(f"\r    [{bar[:30]}] {added}/{limit} added, {skipped} skipped", end="")

            offset += len(docs)
            if len(docs) < fetch_n:
                break  # no more results from API
            time.sleep(0.4)  # be courteous to Open Library

        print()  # newline after progress bar

    return total_added


def run_indian_language(
    db:        Session,
    lang_name: str,
    queries:   list[tuple[str, int]],
    seen_keys: set[str],
    cap:       int | None = None,
) -> int:
    """
    Fetch books for Hindi or Kannada using descriptive query searches.

    WHY NOT USE language=hin/kan DIRECTLY:
      Open Library's search API does not support standalone language-code
      filtering -- the parameter is silently ignored and returns 0 results.
      Searching by subject and author queries surfaces real books in those
      languages that have usable (English) descriptions in Open Library's catalog.
      We then label them with the correct language in our DB.

    queries: list of (search_query, target_count) tuples
    cap:     optional hard cap on total books added across all queries
    """
    total_added  = 0
    total_target = sum(t for _, t in queries)
    if cap:
        total_target = min(total_target, cap)
    print(f"\n[{lang_name}] Importing across {len(queries)} targeted queries (target ~{total_target})...")

    for query, per_query_target in queries:
        if cap and total_added >= cap:
            break
        limit  = min(per_query_target, cap - total_added) if cap else per_query_target
        added  = 0
        offset = 0
        print(f"  Query: '{query}' (target {limit})")

        while added < limit:
            fetch_n = min(100, limit - added)
            docs    = _fetch_page(query=query, limit=fetch_n, offset=offset)
            if not docs:
                break

            # Force-label these books as the target language.
            # Many Indian books in Open Library lack the 'language' field,
            # but their content is clearly in Hindi or Kannada based on the query.
            new_books, skipped = import_books(db, docs, lang_name, seen_keys)
            for book in new_books:
                book.language = lang_name   # override whatever OL said

            if new_books:
                db.add_all(new_books)
                db.flush()
                embed_and_save(db, new_books)
                added       += len(new_books)
                total_added += len(new_books)

            bar = "#" * min(added, limit) + "." * max(0, limit - added)
            print(f"\r    [{bar[:30]}] {added}/{limit} added, {skipped} skipped", end="")

            offset += len(docs)
            if len(docs) < fetch_n:
                break
            time.sleep(0.4)

        print()

    return total_added


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Bulk-import books from Open Library into the local database."
    )
    parser.add_argument(
        "--mode",
        choices=["english", "hindi", "kannada", "all"],
        default="all",
        help="Which language(s) to import (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap on books to add per subject/language (default: use built-in targets)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  BOOK VIBE -- BULK IMPORT")
    print("=" * 60)
    print(f"  Mode  : {args.mode}")
    print(f"  Limit : {args.limit or 'built-in targets'}")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Load all existing OL keys into memory once so dedup checks are O(1)
        existing_keys: set[str] = {
            row[0]
            for row in db.query(Book.ol_key).filter(Book.ol_key.isnot(None)).all()
        }

        before = db.query(Book).count()
        print(f"\n  Books in DB before import: {before}")

        total = 0

        if args.mode in ("english", "all"):
            total += run_english(db, existing_keys, args.limit)

        if args.mode in ("hindi", "all"):
            total += run_indian_language(
                db, "Hindi", HINDI_QUERIES, existing_keys, cap=args.limit
            )

        if args.mode in ("kannada", "all"):
            total += run_indian_language(
                db, "Kannada", KANNADA_QUERIES, existing_keys, cap=args.limit
            )

        after = db.query(Book).count()

    finally:
        db.close()

    print("\n" + "=" * 60)
    print(f"  [OK] Import complete.")
    print(f"  [OK] Books before : {before}")
    print(f"  [OK] Books added  : {total}")
    print(f"  [OK] Books now    : {after}")

    by_lang = {}
    db2 = SessionLocal()
    try:
        for lang in ("English", "Hindi", "Kannada"):
            n = db2.query(Book).filter(Book.language == lang).count()
            by_lang[lang] = n
        other = db2.query(Book).filter(
            ~Book.language.in_(["English", "Hindi", "Kannada"])
        ).count()
    finally:
        db2.close()

    print(f"\n  Breakdown by language:")
    for lang, n in by_lang.items():
        print(f"    {lang:<12} {n}")
    if other:
        print(f"    Other        {other}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
