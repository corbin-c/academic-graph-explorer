"""Person detail endpoint — fetches from IdRef SPARQL (cached)."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.database import get_session
from app.domain.entity import Contribution, OrganizationRef, Person
from app.sources.client import SparqlQueryError
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/person", tags=["person"])

# Load SPARQL query templates (read once at module load)
_query_prefix = Path(__file__).resolve().parent.parent / "sources" / "idref" / "queries"
PERSON_QUERY = (_query_prefix / "person.sparql").read_text()
CONTRIBUTIONS_QUERY = (_query_prefix / "person_contributions.sparql").read_text()


async def get_idref_client(
    session: AsyncSession = Depends(get_session),
) -> IdRefSparqlClient:
    """Provide an IdRef SPARQL client with optional cache session."""
    return IdRefSparqlClient(cache_session=session)


def _normalize_person_id(person_id: str) -> str:
    """Accept raw PPN or full URI, return IdRef person URI."""
    if person_id.startswith("http://") or person_id.startswith("https://"):
        return person_id
    return f"http://www.idref.fr/{person_id}/id"


def _parse_person_bindings(person_id: str, bindings: list[dict]) -> Person:
    """Aggregate SPARQL bindings into a Person model."""
    name = None
    note = None
    orgs: list[str] = []

    for b in bindings:
        if name is None:
            name = b["name"]["value"]
        if note is None and "note" in b:
            note = b["note"]["value"]
        if "org" in b and "orgName" in b:
            org_name = b["orgName"]["value"]
            if org_name not in orgs:
                orgs.append(org_name)

    if name is None:
        raise ValueError("No name found in SPARQL bindings for person")

    return Person(
        id=person_id,
        name=name,
        note=note,
        organizations=[OrganizationRef(name=o) for o in orgs],
    )


# ── Sub-resource routes (must be before the catch-all) ──


@router.get("/{person_id:path}/contributions")
async def get_person_contributions(
    person_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get co-authored publications for a person from IdRef."""
    person_uri = _normalize_person_id(person_id)
    query = CONTRIBUTIONS_QUERY.replace("$person", f"<{person_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])

    return [
        Contribution(
            id=b["doc"]["value"],
            title=b["title"]["value"],
            role=b.get("role", {}).get("value") if "role" in b else None,
            co_author_name=b.get("author_name", {}).get("value")
            if "author_name" in b
            else None,
        )
        for b in bindings
    ]


# ── Catch-all detail route ──


@router.get("/{person_id:path}")
async def get_person(
    person_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get detailed information about a person from IdRef.

    Accepts raw PPN (e.g. "121375307") or full IdRef URI
    (e.g. "http://www.idref.fr/121375307/id").
    """
    person_uri = _normalize_person_id(person_id)
    query = PERSON_QUERY.replace("$person", f"<{person_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Person not found")

    return _parse_person_bindings(person_id, bindings)
