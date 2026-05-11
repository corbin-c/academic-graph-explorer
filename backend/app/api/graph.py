"""
Graph traversal endpoint — BFS over the IdRef knowledge graph.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.database import get_session
from app.domain.entity import EntityType
from app.domain.graph import Neighborhood
from app.sources.client import SparqlQueryError
from app.sources.idref.sparql import IdRefSparqlClient
from app.services.graph_traversal import GraphTraverser

router = APIRouter(prefix="/graph", tags=["graph"])


async def get_idref_client(
    session: AsyncSession = Depends(get_session),
) -> IdRefSparqlClient:
    """Provide an IdRef SPARQL client with optional cache session."""
    return IdRefSparqlClient(cache_session=session)


@router.get("/", response_model=Neighborhood)
async def traverse_graph(
    root: str = Query(
        ..., min_length=1, description="Starting entity ID (PPN or full URI)"
    ),
    type: str = Query(
        ..., description="Entity type: person, organization, or publication"
    ),
    depth: int = Query(2, ge=1, le=10, description="Number of hops from root"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum nodes returned"),
    client: IdRefSparqlClient = Depends(get_idref_client),
):
    """Progressive graph exploration starting from a root entity.

    Returns a bounded Neighborhood: the center entity, all discovered
    nodes, and the edges between them.
    """
    try:
        entity_type = EntityType(type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid type: '{type}'. Must be one of: person, organization, publication",
        )

    traverser = GraphTraverser(client)

    try:
        return await traverser.traverse(root, entity_type, depth, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
