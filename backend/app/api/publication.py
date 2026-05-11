"""Publication detail and sub-resource endpoints (cached)."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.database import get_session
from app.domain.entity import Identifier, OrgRole, PersonRole, Publication
from app.sources.client import SparqlQueryError
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/publication", tags=["publication"])

_query_prefix = Path(__file__).resolve().parent.parent / "sources" / "idref" / "queries"


async def get_idref_client(
    session: AsyncSession = Depends(get_session),
) -> IdRefSparqlClient:
    """Provide an IdRef SPARQL client with optional cache session."""
    return IdRefSparqlClient(cache_session=session)


def _normalize_publication_id(raw: str) -> str:
    """Normalize a raw PPN or full URI to a canonical IdRef URI."""
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    return f"http://www.idref.fr/{raw}/id"


def _parse_publication_bindings(bindings: list[dict], pub_id: str) -> Publication:
    """Parse SPARQL bindings into a Publication model."""
    if not bindings:
        raise ValueError("No bindings to parse")

    title = None
    doi = None
    identifiers: list[Identifier] = []

    for b in bindings:
        if title is None and "title" in b:
            title = b["title"]["value"]

        if doi is None and "doi" in b and "value" in b["doi"]:
            doi = b["doi"]["value"]

        if "sameAs" in b:
            identifiers.append(
                Identifier(scheme="owl:sameAs", value=b["sameAs"]["value"])
            )

        if "uri" in b:
            identifiers.append(Identifier(scheme="bibo:uri", value=b["uri"]["value"]))

    if title is None:
        raise ValueError("Publication title not found in SPARQL response")

    return Publication(id=pub_id, title=title, doi=doi, identifiers=identifiers)


def _parse_person_role_bindings(bindings: list[dict]) -> list[PersonRole]:
    """Parse SPARQL bindings into a list of PersonRole."""
    results: list[PersonRole] = []
    for b in bindings:
        person_id = b.get("person", {}).get("value", "")
        name = b.get("person_name", {}).get("value")
        role = b.get("person_role", {}).get("value")
        if name:
            results.append(PersonRole(id=person_id, name=name, role=role))
    return results


def _parse_org_role_bindings(bindings: list[dict]) -> list[OrgRole]:
    """Parse SPARQL bindings into a list of OrgRole."""
    results: list[OrgRole] = []
    for b in bindings:
        org_id = b.get("org", {}).get("value", "")
        name = b.get("org_name", {}).get("value")
        role = b.get("org_role", {}).get("value")
        if name:
            results.append(OrgRole(id=org_id, name=name, role=role))
    return results


@router.get("/{publication_id:path}/persons")
async def get_publication_persons(
    publication_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get persons linked to a publication."""
    pub_uri = _normalize_publication_id(publication_id)
    query = (
        (_query_prefix / "publication_persons.sparql")
        .read_text()
        .replace("$publication", f"<{pub_uri}>")
    )

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    return _parse_person_role_bindings(bindings)


@router.get("/{publication_id:path}/organizations")
async def get_publication_organizations(
    publication_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get organizations linked to a publication."""
    pub_uri = _normalize_publication_id(publication_id)
    query = (
        (_query_prefix / "publication_organizations.sparql")
        .read_text()
        .replace("$publication", f"<{pub_uri}>")
    )

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    return _parse_org_role_bindings(bindings)


@router.get("/{publication_id:path}")
async def get_publication(
    publication_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get detailed information about a publication."""
    pub_uri = _normalize_publication_id(publication_id)
    query = (
        (_query_prefix / "publication.sparql")
        .read_text()
        .replace("$publication", f"<{pub_uri}>")
    )

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(
            status_code=404, detail=f"Publication not found: {publication_id}"
        )

    try:
        return _parse_publication_bindings(bindings, pub_uri)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
