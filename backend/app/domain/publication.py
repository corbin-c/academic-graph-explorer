"""
Publication-specific domain model.
"""

from pydantic import BaseModel


class Publication(BaseModel):
    id: str
    title: str
    doi: str | None = None
    year: int | None = None
