"""Publication detail endpoints (stub)."""

from fastapi import APIRouter

router = APIRouter(prefix="/publication", tags=["publication"])


@router.get("/{publication_id:path}")
async def get_publication(publication_id: str):
    """Get detailed information about a publication."""
    return {"message": f"Publication {publication_id} — not yet implemented"}
