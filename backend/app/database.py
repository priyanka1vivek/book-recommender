"""
database.py — SQLAlchemy engine + session factory.

SQLAlchemy is the "translator" between Python objects and the SQLite database file.
Instead of writing raw SQL like INSERT INTO books..., we work with Python classes
and SQLAlchemy generates the SQL for us. This also means swapping to PostgreSQL
in production requires changing exactly one line: DATABASE_URL.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# Reads DATABASE_URL from .env file. Falls back to a local SQLite file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/books.db")

# check_same_thread=False is required for SQLite + FastAPI because FastAPI
# can handle multiple requests on different threads simultaneously.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # set True to print every SQL statement (useful for debugging)
)

# A SessionLocal is a "connection" to the database. We open one per request
# and close it when the request finishes (the get_db function below handles this).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM model classes inherit from this. It tells SQLAlchemy what tables exist."""
    pass


def get_db():
    """
    FastAPI dependency — opens a DB session for a request and guarantees
    it closes even if the request crashes.
    Usage in routers: def my_endpoint(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
