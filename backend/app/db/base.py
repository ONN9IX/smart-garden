"""Declarative base for Alembic metadata. Tables are created by migrations only."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
