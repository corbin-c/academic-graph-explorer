"""
Search endpoint — not yet implemented (was IdRef SOLR, will be refactored to SPARQL).
"""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
):
    return {
        "message": "Search endpoint — not yet implemented via SPARQL",
        "query": q,
    }
