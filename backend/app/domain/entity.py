"""
Core domain models for academic graph nodes.

Entity is the base type with three discriminated subclasses:
Person, Organization, and Publication. Each carries its own
context-specific fields (e.g., Person has organizations, Publication
has a doi). The `type` field uses a Literal discriminator so Pydantic
serializes the concrete subclass even when the list is typed as list[Entity].
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class EntityType(StrEnum):
    PERSON = "person"
    PUBLICATION = "publication"
    ORGANIZATION = "organization"


class Identifier(BaseModel):
    """An external identifier (ORCID, DOI, ROR, IdRef, etc.)."""

    scheme: str
    value: str


def dedup_identifiers(identifiers: list[Identifier]) -> list[Identifier]:
    """Deduplicate identifiers by (scheme, value) while preserving order."""
    seen: set[tuple[str, str]] = set()
    result: list[Identifier] = []
    for ident in identifiers:
        key = (ident.scheme, ident.value)
        if key not in seen:
            seen.add(key)
            result.append(ident)
    return result


class Entity(BaseModel):
    """Base node in the academic graph.

    Subclasses: Person, Organization, Publication.
    The `type` discriminator ensures Pydantic serializes the concrete type
    even when held in a list[Entity] (e.g., Neighborhood.nodes).
    """

    id: str
    label: str
    type: EntityType
    identifiers: list[Identifier] = []


class Organization(Entity):
    """An organization (institution, lab, funder, etc.)."""

    type: Literal[EntityType.ORGANIZATION] = EntityType.ORGANIZATION
    note: str | None = None


class Person(Entity):
    """A person (researcher, author, director, etc.).

    Limited to simple self-referencing: person has Organization
    memberships. Organization is defined before Person to avoid
    forward-reference issues with Pydantic.
    """

    type: Literal[EntityType.PERSON] = EntityType.PERSON
    note: str | None = None
    organizations: list[Organization] = []


class Publication(Entity):
    """A publication (article, book, thesis, etc.)."""

    type: Literal[EntityType.PUBLICATION] = EntityType.PUBLICATION
    doi: str | None = None
    identifiers: list[Identifier] = []
