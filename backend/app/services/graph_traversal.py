"""Graph traversal engine — BFS over the IdRef knowledge graph."""

from collections import deque

from app.domain.entity import (
    Entity,
    EntityType,
    Identifier,
    Organization,
    Person,
    Publication,
    dedup_identifiers,
)
from app.domain.graph import Neighborhood
from app.domain.relationship import Dataset, EntityId, Relationship
from app.normalize import normalize_idref_id
from app.sources.client import SparqlQueryError
from app.sources.idref.queries import (
    ORGANIZATION,
    ORGANIZATION_MEMBERS,
    ORGANIZATION_PUBLICATIONS,
    PERSON,
    PERSON_CONTRIBUTIONS,
    PUBLICATION,
    PUBLICATION_ORGANIZATIONS,
    PUBLICATION_PERSONS,
)
from app.sources.idref.sparql import IDREF_ENDPOINT, IdRefSparqlClient

IDREF_DATASET = Dataset(name="IdRef", endpoint=IDREF_ENDPOINT)

# ── SPARQL templates ──────────────────────────────────────────

_ENTITY_QUERIES = {
    EntityType.PERSON: PERSON,
    EntityType.ORGANIZATION: ORGANIZATION,
    EntityType.PUBLICATION: PUBLICATION,
}

# For PERSON, the entity query (person.sparql) already returns org
# relationships inline via ?org — no separate query needed.
_INLINE_RELATIONS: dict[EntityType, tuple[EntityType, str, str]] = {
    EntityType.PERSON: (EntityType.ORGANIZATION, "org", "affiliatedWith"),
}

# Additional relationship queries needed beyond the entity query.
# Each entry: (neighbor_type, query_template, binding_key, role_label)
_ADDITIONAL_RELATIONS: dict[
    EntityType, list[tuple[EntityType, str, str, str | None]]
] = {
    EntityType.PERSON: [
        (EntityType.PUBLICATION, PERSON_CONTRIBUTIONS, "doc", "authorOf"),
    ],
    EntityType.ORGANIZATION: [
        (EntityType.PERSON, ORGANIZATION_MEMBERS, "person", "memberOf"),
        (EntityType.PUBLICATION, ORGANIZATION_PUBLICATIONS, "doc", "produced"),
        # Also extract authors linked to the organization's publications
        (EntityType.PERSON, ORGANIZATION_PUBLICATIONS, "author", "authorOf"),
    ],
    EntityType.PUBLICATION: [
        (EntityType.PERSON, PUBLICATION_PERSONS, "person", None),
        (EntityType.ORGANIZATION, PUBLICATION_ORGANIZATIONS, "org", None),
    ],
}

_PARAM_NAMES: dict[EntityType, str] = {
    EntityType.PERSON: "$person",
    EntityType.ORGANIZATION: "$organization",
    EntityType.PUBLICATION: "$publication",
}


def _parse_entity_bindings(
    entity_type: EntityType, entity_uri: str, bindings: list[dict]
) -> Entity:
    """Parse SPARQL bindings into an Entity (concrete subclass)."""
    if not bindings:
        raise ValueError(f"No bindings for {entity_type} {entity_uri}")

    if entity_type == EntityType.PERSON:
        name = bindings[0]["name"]["value"]
        return Person(id=entity_uri, label=name)

    elif entity_type == EntityType.ORGANIZATION:
        name = bindings[0]["name"]["value"]
        return Organization(id=entity_uri, label=name)

    elif entity_type == EntityType.PUBLICATION:
        title = bindings[0]["title"]["value"]
        identifiers: list[Identifier] = []
        for b in bindings:
            if "sameAs" in b:
                identifiers.append(
                    Identifier(scheme="owl:sameAs", value=b["sameAs"]["value"])
                )
            if "uri" in b:
                identifiers.append(
                    Identifier(scheme="bibo:uri", value=b["uri"]["value"])
                )
        return Publication(
            id=entity_uri,
            label=title,
            identifiers=dedup_identifiers(identifiers),
        )

    raise ValueError(f"Unknown entity type: {entity_type}")


def _extract_neighbor_ids(
    bindings: list[dict], binding_key: str
) -> dict[str, str | None]:
    """Extract unique neighbor URIs with optional role from bindings.

    Returns dict mapping neighbor_id → role (or None if no role key).
    """
    ids: dict[str, str | None] = {}
    role_key = binding_key + "_role"
    for b in bindings:
        if binding_key in b:
            nid = b[binding_key]["value"]
            if nid not in ids:
                role = b.get(role_key, {}).get("value") if role_key in b else None
                ids[nid] = role
    return ids


def _infer_edge_role(
    source_type: EntityType,
    target_type: EntityType,
    fallback: str,
    role_from_query: str | None,
) -> str:
    """Return the edge role, preferring query-provided role over fallback."""
    return role_from_query if role_from_query else fallback


class GraphTraverser:
    """Breadth-first graph traversal over the IdRef knowledge graph."""

    def __init__(self, client: IdRefSparqlClient):
        self._client = client
        self._queried_queries: set[str] = set()  # cache key set for dedup

    async def traverse(
        self,
        root_id: str,
        root_type: EntityType,
        max_depth: int,
        max_nodes: int,
    ) -> Neighborhood:
        """BFS traversal returning a Neighborhood of nodes and edges."""
        root_uri = normalize_idref_id(root_id)

        visited: set[str] = {root_uri}
        nodes: dict[str, Entity] = {}
        edges: dict[tuple, Relationship] = {}
        frontier: deque[tuple[str, EntityType, int]] = deque([(root_uri, root_type, 0)])

        while frontier:
            current_id, current_type, current_depth = frontier.popleft()

            if current_id in nodes:
                continue

            query = _ENTITY_QUERIES[current_type].replace(
                _PARAM_NAMES[current_type], f"<{current_id}>"
            )
            try:
                result = await self._client.cached_query(query)
                bindings = result.get("results", {}).get("bindings", [])
                entity = _parse_entity_bindings(current_type, current_id, bindings)
            except (SparqlQueryError, KeyError, ValueError):
                continue

            nodes[current_id] = entity

            if len(nodes) >= max_nodes:
                break

            # ── Inline relationships ────────────────────────────
            if current_type in _INLINE_RELATIONS:
                neighbor_type, binding_key, role_fallback = _INLINE_RELATIONS[
                    current_type
                ]
                neighbor_ids = _extract_neighbor_ids(bindings, binding_key)
                for neighbor_id, role in neighbor_ids.items():
                    edge_role = _infer_edge_role(
                        current_type, neighbor_type, role_fallback, role
                    )
                    edge = Relationship(
                        source=EntityId(current_id),
                        target=EntityId(neighbor_id),
                        type=edge_role,
                        source_dataset=IDREF_DATASET,
                    )
                    edges[(edge.source, edge.target, edge.type)] = edge
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        if len(nodes) < max_nodes:
                            frontier.append(
                                (neighbor_id, neighbor_type, current_depth + 1)
                            )

            # ── Additional relationship queries ─────────────────
            if current_depth < max_depth and current_type in _ADDITIONAL_RELATIONS:
                for (
                    neighbor_type,
                    rel_query,
                    binding_key,
                    role_fallback,
                ) in _ADDITIONAL_RELATIONS[current_type]:
                    try:
                        rq = rel_query.replace(
                            _PARAM_NAMES[current_type], f"<{current_id}>"
                        )
                        result = await self._client.cached_query(rq)
                        rel_bindings = result.get("results", {}).get("bindings", [])
                    except SparqlQueryError:
                        continue

                    neighbor_ids = _extract_neighbor_ids(rel_bindings, binding_key)
                    for neighbor_id, role in neighbor_ids.items():
                        edge_role = _infer_edge_role(
                            current_type,
                            neighbor_type,
                            role_fallback or "relatedTo",
                            role,
                        )
                        edge = Relationship(
                            source=EntityId(current_id),
                            target=EntityId(neighbor_id),
                            type=edge_role,
                            source_dataset=IDREF_DATASET,
                        )
                        edges[(edge.source, edge.target, edge.type)] = edge
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            if len(nodes) < max_nodes:
                                frontier.append(
                                    (neighbor_id, neighbor_type, current_depth + 1)
                                )

        if root_uri not in nodes:
            raise ValueError(f"Could not resolve root entity: {root_uri}")

        return Neighborhood(
            center=nodes[root_uri],
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )
