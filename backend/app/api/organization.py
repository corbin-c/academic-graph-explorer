"""Organization endpoints — fetches from IdRef SPARQL (cached)."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_idref_client
from app.domain.entity import Organization, PersonRef, PublicationRef
from app.normalize import normalize_idref_id
from app.sources.client import SparqlQueryError
from app.sources.idref.queries import (
    ORGANIZATION,
    ORGANIZATION_MEMBERS,
    ORGANIZATION_PUBLICATIONS,
)
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/organization", tags=["organization"])


def _parse_org_bindings(org_id: str, bindings: list[dict]) -> Organization:
    """Parse SPARQL bindings into an Organization model."""
    name = None
    note = None

    for b in bindings:
        if name is None and "name" in b:
            name = b["name"]["value"]
        if note is None and "note" in b:
            note = b["note"]["value"]

    if name is None:
        raise ValueError("No name found in SPARQL bindings for organization")

    return Organization(id=org_id, name=name, note=note)


@router.get("/{organization_id:path}/members")
async def get_organization_members(
    organization_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get members (persons) of an organization from IdRef."""
    org_uri = normalize_idref_id(organization_id)
    query = ORGANIZATION_MEMBERS.replace("$organization", f"<{org_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])

    return [
        PersonRef(id=b["person"]["value"], name=b["name"]["value"]) for b in bindings
    ]


@router.get("/{organization_id:path}/publications")
async def get_organization_publications(
    organization_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get publications affiliated with an organization from IdRef."""
    org_uri = normalize_idref_id(organization_id)
    query = ORGANIZATION_PUBLICATIONS.replace("$organization", f"<{org_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])

    return [
        PublicationRef(
            id=b["doc"]["value"],
            title=b["title"]["value"],
            author_name=b.get("author_name", {}).get("value")
            if "author_name" in b
            else None,
        )
        for b in bindings
    ]


@router.get("/{organization_id:path}")
async def get_organization(
    organization_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get detailed information about an organization from IdRef.

    Accepts raw PPN (e.g. "227816196") or full IdRef URI
    (e.g. "http://www.idref.fr/227816196/id").
    """
    org_uri = normalize_idref_id(organization_id)
    query = ORGANIZATION.replace("$organization", f"<{org_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Organization not found")

    return _parse_org_bindings(organization_id, bindings)
