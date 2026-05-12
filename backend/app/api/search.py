"""
Search endpoint — queries IdRef SOLR via SRU.
"""

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.domain.search import SearchResult
from app.sources.idref.search import IdRefSearchClient

router = APIRouter(prefix="/search", tags=["search"])

# Allowed recordtype_z values and their type mapping
_RECORDTYPE_MAP = {
    "a": "person",
    "b": "organization",
}


@router.get("/", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
):
    """Search for persons and organizations in IdRef via SOLR."""
    client = IdRefSearchClient()

    try:
        docs = await client.search(q)
    except (httpx.HTTPError, httpx.RequestError) as e:
        raise HTTPException(
            status_code=502, detail=f"IdRef SOLR search failed: {e}"
        ) from e

    results: list[SearchResult] = []
    for doc in docs:
        recordtype = doc.get("recordtype_z", "")
        entity_type = _RECORDTYPE_MAP.get(recordtype)
        if entity_type is None:
            continue  # Skip unknown record types
        results.append(
            SearchResult(
                id=doc["ppn_z"],
                name=doc["affcourt_z"],
                type=entity_type,
            )
        )

    return results
