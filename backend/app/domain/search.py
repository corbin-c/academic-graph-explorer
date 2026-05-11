"""Search domain models."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A search result from IdRef SOLR."""

    id: str  # ppn_z
    name: str  # affcourt_z
    type: str  # "person" or "organization"
