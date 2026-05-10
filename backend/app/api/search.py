from fastapi import APIRouter, Query

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search(q: str = Query(..., min_length=1, description="Search query")):
    """Search for academic entities by name or identifier."""
    return {"message": f"Search for '{q}' — not yet implemented"}
