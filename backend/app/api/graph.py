"""
Graph traversal endpoint — BFS over the IdRef knowledge graph.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_idref_client
from app.cache.database import get_session
from app.domain.entity import EntityType
from app.domain.graph import Neighborhood
from app.services.continuation import create_session, load_session, update_session
from app.services.graph_traversal import GraphTraverser, TraversalState
from app.sources.client import SparqlQueryError
from app.sources.idref.sparql import IdRefSparqlClient

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/", response_model=Neighborhood)
async def traverse_graph(
    root: str = Query(
        ..., min_length=1, description="Starting entity ID (PPN or full URI)"
    ),
    type: str = Query(
        ..., description="Entity type: person, organization, or publication"
    ),
    depth: int = Query(2, ge=1, le=10, description="Number of hops from root"),
    max_nodes: int = Query(40, ge=1, description="Maximum number of nodes to return"),
    max_edges: int = Query(80, ge=1, description="Maximum number of edges to return"),
    continuation: str | None = Query(
        None, description="Continuation session id from a prior truncated response"
    ),
    client: IdRefSparqlClient = Depends(get_idref_client),
    session: AsyncSession = Depends(get_session),
):
    """Progressive graph exploration starting from a root entity.

    Returns a bounded Neighborhood: the center entity, all discovered
    nodes, and the edges between them. When truncated, a ``continuation_id``
    is returned so a follow-up request can fetch the next chunk.
    """
    try:
        entity_type = EntityType(type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid type: '{type}'. Must be one of: person, organization, publication",
        )

    try:
        state: TraversalState | None = None
        if continuation is not None:
            state_dict = await load_session(session, continuation)
            if state_dict is None:
                raise HTTPException(
                    status_code=404, detail="continuation session not found or expired"
                )
            state = TraversalState.from_dict(state_dict)

        traverser = GraphTraverser(client)
        result = await traverser.traverse(
            root, entity_type, depth, max_nodes, max_edges, state
        )

        if result.next_state is not None:
            if continuation is not None:
                await update_session(session, continuation, result.next_state.to_dict())
                continuation_id = continuation
            else:
                continuation_id = await create_session(
                    session, result.next_state.to_dict()
                )
            result.neighborhood.continuation_id = continuation_id

        return result.neighborhood
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SparqlQueryError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
