"""Person detail endpoint — fetches from IdRef SPARQL."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.domain.entity import OrganizationRef, Person
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/person", tags=["person"])

# Load the SPARQL query template
_query_path = (
    Path(__file__).resolve().parent.parent
    / "sources"
    / "idref"
    / "queries"
    / "person.sparql"
)
PERSON_QUERY = _query_path.read_text()


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


@router.get("/{person_id:path}")
async def get_person(person_id: str):
    """Get detailed information about a person from IdRef.

    Accepts raw PPN (e.g. "121375307") or full IdRef URI
    (e.g. "http://www.idref.fr/121375307/id").
    """
    person_uri = _normalize_person_id(person_id)
    query = PERSON_QUERY.replace("$person", f"<{person_uri}>")

    client = IdRefSparqlClient()
    result = await client.query(query)

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Person not found")

    return _parse_person_bindings(person_id, bindings)
