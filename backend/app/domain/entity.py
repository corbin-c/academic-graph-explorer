"""
Core entity model for academic graph nodes.

Every node in the graph is an Entity with a type, label, and optional
external identifiers.
"""

from enum import StrEnum

from pydantic import BaseModel


class EntityType(StrEnum):
    PERSON = "person"
    PUBLICATION = "publication"
    PROJECT = "project"
    INSTITUTION = "institution"
    DATASET = "dataset"


class Identifier(BaseModel):
    """An external identifier (ORCID, DOI, ROR, IdRef, etc.)."""

    scheme: str
    value: str


class Entity(BaseModel):
    """A node in the academic graph."""

    id: str
    label: str
    type: EntityType
    identifiers: list[Identifier] = []
