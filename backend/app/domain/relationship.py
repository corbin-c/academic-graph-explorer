"""
Relationship model for edges in the academic graph.
"""

from enum import StrEnum
from typing import NewType

from pydantic import BaseModel

EntityId = NewType("EntityId", str)


class RelationshipType(StrEnum):
    AUTHOR_OF = "authorOf"
    CITES = "cites"
    AFFILIATED_WITH = "affiliatedWith"
    CONTRIBUTES_TO = "contributesTo"
    PART_OF = "partOf"
    PRODUCED = "produced"
    FUNDED_BY = "fundedBy"
    SUPERVISES = "supervises"


class Dataset(BaseModel):
    """The data source from which a relationship was retrieved."""

    name: str
    endpoint: str | None = None


class Relationship(BaseModel):
    """A directional relationship between two entities."""

    source: EntityId
    target: EntityId
    type: RelationshipType
    source_dataset: Dataset
