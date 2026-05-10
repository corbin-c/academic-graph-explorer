"""
Domain models for academic entities.

Defines typed containers for Person, Publication, Project, Institution, Dataset.
"""

from pydantic import BaseModel


class Person(BaseModel):
    id: str
    name: str
    orcid: str | None = None


class Publication(BaseModel):
    id: str
    title: str
    doi: str | None = None
    year: int | None = None


class Institution(BaseModel):
    id: str
    name: str
    ror_id: str | None = None


class Project(BaseModel):
    id: str
    title: str
    grant_id: str | None = None


class Dataset(BaseModel):
    id: str
    title: str
    doi: str | None = None
