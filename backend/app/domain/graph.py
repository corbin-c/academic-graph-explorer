"""
Domain model for the academic graph.

The graph is composed of Entities (nodes) and Relationships (edges).
A Neighborhood is a bounded subgraph around a central entity.
"""

from pydantic import BaseModel

from app.domain.entity import Entity
from app.domain.relationship import Relationship


class Neighborhood(BaseModel):
    """A bounded neighborhood of the graph around a central entity."""

    center: Entity
    nodes: list[Entity]
    edges: list[Relationship]
