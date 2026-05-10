from fastapi import APIRouter

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/{entity_id}")
async def get_entity(entity_id: str):
    """Get details for a specific academic entity."""
    return {"message": f"Entity {entity_id} — not yet implemented"}


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(entity_id: str):
    """Get relationships for a specific academic entity."""
    return {"message": f"Relationships for entity {entity_id} — not yet implemented"}


@router.get("/{entity_id}/contributions")
async def get_entity_contributions(entity_id: str):
    """Get contributions for a specific academic entity."""
    return {"message": f"Contributions for entity {entity_id} — not yet implemented"}
