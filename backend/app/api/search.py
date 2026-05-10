from fastapi import APIRouter, Query

from app.domain.search import SearchResult
from app.sources.idref.search import IdRefSearchClient

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
) -> list[SearchResult]:
    """Search for academic entities by name via IdRef SOLR."""
    client = IdRefSearchClient()
    raw = await client.search_person(q)
    docs = raw.get("response", {}).get("docs", [])
    return [
        SearchResult(
            name=doc["affcourt_z"],
            ppn=doc["ppn_z"],
            identifiers=doc.get("idsext_s", []),
        )
        for doc in docs
    ]
