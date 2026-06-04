"""
models/book.py — The Book table definition.

Each Python class attribute that wraps Column(...) becomes one column in SQLite.
SQLAlchemy reads this class at startup and creates the table automatically via
Base.metadata.create_all() in main.py.

We do NOT store embedding vectors in SQLite — they are too wide to index efficiently
and SQLite has no native vector-distance operator. Instead we store them as a JSON
string (embedding_json) that numpy deserialises at query time for cosine similarity.
"""

from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id             = Column(Integer,      primary_key=True, index=True)
    title          = Column(String(512),  nullable=False, index=True)
    author         = Column(String(256),  nullable=False)
    description    = Column(Text,         nullable=False)
    genre          = Column(String(128),  nullable=False)
    # language — e.g. "English", "Hindi", "Kannada"
    # Nullable so older records without the column still load cleanly.
    language       = Column(String(64),   nullable=True, index=True)
    year           = Column(Integer,      nullable=True)
    cover_url      = Column(String(1024), nullable=True)
    isbn           = Column(String(32),   nullable=True)
    # Open Library Works ID — deduplication key when importing via /books/discover
    ol_key         = Column(String(64),   nullable=True, unique=True, index=True)
    # 384-float vector stored as JSON, e.g. "[0.021, -0.134, ..., 0.087]"
    # NULL = book exists but has not been embedded yet.
    embedding_json = Column(Text,         nullable=True)

    def __repr__(self):
        return f"<Book id={self.id} title='{self.title}' language='{self.language}'>"
