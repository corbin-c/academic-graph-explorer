"""Publication detail endpoint — fetches from IdRef SPARQL (cached)."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_idref_client
from app.domain.entity import Identifier, Publication, dedup_identifiers
from app.normalize import normalize_idref_id
from app.sources.client import SparqlQueryError
from app.sources.idref.queries import PUBLICATION
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/publication", tags=["publication"])


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

    return Publication(
        id=pub_id,
        label=title,
        doi=doi,
        identifiers=dedup_identifiers(identifiers),
    )


@router.get("/{publication_id}", response_model=Publication)
async def get_publication(
    publication_id: str,
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Get detailed information about a publication."""
    pub_uri = normalize_idref_id(publication_id)
    query = PUBLICATION.replace("$publication", f"<{pub_uri}>")

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
