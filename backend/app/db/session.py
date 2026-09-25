"""PostgreSQL session factory and FastAPI dependency.

Purpose: transactional database access without a second local database.
Security: URL comes from environment; exceptions roll back the transaction.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
