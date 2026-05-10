from fastapi import APIRouter, Query

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/")
async def traverse_graph(
    root: str = Query(..., min_length=1, description="Starting entity ID"),
    depth: int = Query(2, ge=1, le=10, description="Number of hops from root"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum nodes/edges returned"),
    relations: str | None = Query(
        None,
        description="Comma-separated relation types to include (e.g. authorOf,cites)",
    ),
):
    """
    Progressive graph exploration starting from a root entity.

    Returns a bounded neighborhood: nodes and edges up to the specified depth
    and within the given limit.
    """
    relation_list = (
        [r.strip() for r in relations.split(",") if r.strip()] if relations else None
    )

    return {
        "message": "Graph traversal endpoint — not yet implemented",
        "params": {
            "root": root,
            "depth": depth,
            "limit": limit,
            "relations": relation_list,
        },
    }
