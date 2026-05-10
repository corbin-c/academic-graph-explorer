"""Search-related domain models."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Simplified person search result from IdRef SOLR."""

    name: str
    ppn: str
    identifiers: list[str] = []
