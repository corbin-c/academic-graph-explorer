"""Organization endpoints — fetches from IdRef SPARQL."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.domain.entity import Organization, PersonRef, PublicationRef
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/organization", tags=["organization"])

# Load SPARQL query templates
_query_prefix = Path(__file__).resolve().parent.parent / "sources" / "idref" / "queries"
ORG_QUERY = (_query_prefix / "organization.sparql").read_text()
MEMBERS_QUERY = (_query_prefix / "organization_members.sparql").read_text()
PUBS_QUERY = (_query_prefix / "organization_publications.sparql").read_text()


def _normalize_org_id(org_id: str) -> str:
    """Accept raw PPN or full URI, return IdRef organization URI."""
    if org_id.startswith("http://") or org_id.startswith("https://"):
        return org_id
    return f"http://www.idref.fr/{org_id}/id"


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


# ── Sub-resource routes (must be before the catch-all) ──


@router.get("/{organization_id:path}/members")
async def get_organization_members(organization_id: str):
    """Get members (persons) of an organization from IdRef."""
    org_uri = _normalize_org_id(organization_id)
    query = MEMBERS_QUERY.replace("$organization", f"<{org_uri}>")

    client = IdRefSparqlClient()
    result = await client.query(query)
    bindings = result.get("results", {}).get("bindings", [])

    return [
        PersonRef(
            id=b["person"]["value"],
            name=b["name"]["value"],
        )
        for b in bindings
    ]


@router.get("/{organization_id:path}/publications")
async def get_organization_publications(organization_id: str):
    """Get publications affiliated with an organization from IdRef."""
    org_uri = _normalize_org_id(organization_id)
    query = PUBS_QUERY.replace("$organization", f"<{org_uri}>")

    client = IdRefSparqlClient()
    result = await client.query(query)
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


# ── Catch-all detail route ──


@router.get("/{organization_id:path}")
async def get_organization(organization_id: str):
    """Get detailed information about an organization from IdRef.

    Accepts raw PPN (e.g. "227816196") or full IdRef URI
    (e.g. "http://www.idref.fr/227816196/id").
    """
    org_uri = _normalize_org_id(organization_id)
    query = ORG_QUERY.replace("$organization", f"<{org_uri}>")

    client = IdRefSparqlClient()
    result = await client.query(query)

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Organization not found")

    return _parse_org_bindings(organization_id, bindings)
