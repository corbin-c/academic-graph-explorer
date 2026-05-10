"""
Domain model for the academic graph.

The graph is composed of Nodes (academic entities) and Edges (relationships).
A Neighborhood is a bounded subgraph around a central entity.
"""

from pydantic import BaseModel


class Node(BaseModel):
    """An academic entity in the graph."""

    id: str
    label: str
    type: str  # e.g. Person, Publication, Project, Institution, Dataset


class Edge(BaseModel):
    """A directional relationship between two nodes."""

    source: str
    target: str
    predicate: str  # e.g. authorOf, cites, affiliatedWith


class Neighborhood(BaseModel):
    """A bounded neighborhood of the graph around a central node."""

    center: Node
    nodes: list[Node]
    edges: list[Edge]
