"""
Core domain models for academic graph nodes.
"""

from enum import StrEnum

from pydantic import BaseModel


class EntityType(StrEnum):
    PERSON = "person"
    PUBLICATION = "publication"
    ORGANIZATION = "organization"


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


class OrganizationRef(BaseModel):
    """A lightweight organization reference used in person details."""

    name: str


class Person(BaseModel):
    """Detailed information about a person from IdRef."""

    id: str
    name: str
    note: str | None = None
    organizations: list[OrganizationRef] = []


class Organization(BaseModel):
    """Detailed information about an organization from IdRef."""

    id: str
    name: str
    note: str | None = None
