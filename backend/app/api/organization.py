"""Organization detail endpoint — fetches from IdRef SPARQL."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.domain.entity import Organization
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/organization", tags=["organization"])

# Load the SPARQL query template
_query_path = (
    Path(__file__).resolve().parent.parent
    / "sources"
    / "idref"
    / "queries"
    / "organization.sparql"
)
ORG_QUERY = _query_path.read_text()


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
