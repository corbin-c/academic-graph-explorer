"""Person detail endpoint — fetches from IdRef SPARQL (cached)."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_idref_client
from app.domain.entity import Organization, Person
from app.normalize import normalize_idref_id
from app.sources.client import SparqlQueryError
from app.sources.idref.queries import PERSON
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/person", tags=["person"])


def _parse_person_bindings(person_id: str, bindings: list[dict]) -> Person:
    """Aggregate SPARQL bindings into a Person model."""
    name = None
    note = None
    orgs: dict[str, str] = {}  # id -> name

    for b in bindings:
        if name is None:
            name = b["name"]["value"]
        if note is None and "note" in b:
            note = b["note"]["value"]
        if "org" in b and "orgName" in b:
            org_id = b["org"]["value"]
            org_name = b["orgName"]["value"]
            if org_id not in orgs:
                orgs[org_id] = org_name

    if name is None:
        raise ValueError("No name found in SPARQL bindings for person")

    return Person(
        id=normalize_idref_id(person_id),
        label=name,
        note=note,
        organizations=[
            Organization(id=org_id, label=org_name) for org_id, org_name in orgs.items()
        ],
    )


@router.get("/{person_id:path}")
async def get_person(
    person_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get detailed information about a person from IdRef.

    Accepts raw PPN (e.g. "121375307") or full IdRef URI
    (e.g. "http://www.idref.fr/121375307/id").
    """
    person_uri = normalize_idref_id(person_id)
    query = PERSON.replace("$person", f"<{person_uri}>")

    try:
        result = await client.cached_query(query)
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Person not found")

    return _parse_person_bindings(person_id, bindings)
