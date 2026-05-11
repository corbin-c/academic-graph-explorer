from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class CachedQuery(Base):
    """Cache table for external data source responses."""

    __tablename__ = "cached_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    query_hash = Column(String, nullable=False, unique=True, index=True)
    response_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ttl_seconds = Column(Integer, default=3600, nullable=False)
