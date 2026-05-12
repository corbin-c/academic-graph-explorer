"""
Relationship model for edges in the academic graph.

The relationship type is a free-form string (e.g., "authorOf",
"affiliatedWith", "produced") rather than a closed enum, because
SPARQL endpoints return diverse roles that we relay directly.
"""

from typing import NewType

from pydantic import BaseModel

EntityId = NewType("EntityId", str)


class Dataset(BaseModel):
    """The data source from which a relationship was retrieved."""

    name: str
    endpoint: str | None = None


class Relationship(BaseModel):
    """A directional relationship between two entities.

    The `type` field carries the role from the data source
    (e.g., "author", "directedBy", "host"). It is free-form.
    """

    source: EntityId
    target: EntityId
    type: str
    source_dataset: Dataset
