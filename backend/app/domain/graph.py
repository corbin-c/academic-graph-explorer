"""
Domain model for the academic graph.

The graph is composed of Entities (nodes) and Relationships (edges).
A Neighborhood is a bounded subgraph around a central entity.

Uses a discriminated union on the `type` field so that Pydantic
serializes concrete Entity subclasses (Person, Organization, Publication)
even when held in the polymorphic `nodes` list.
"""

from typing import Annotated, Union

from pydantic import BaseModel, Field

from app.domain.entity import Entity, Organization, Person, Publication
from app.domain.relationship import Relationship

EntityNode = Annotated[
    Union[Person, Organization, Publication],
    Field(discriminator="type"),
]


class Neighborhood(BaseModel):
    """A bounded neighborhood of the graph around a central entity."""

    center: Entity
    nodes: list[EntityNode]
    edges: list[Relationship]
    truncated: bool = False
    continuation_id: str | None = None
