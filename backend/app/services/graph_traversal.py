"""Graph traversal engine — BFS over the IdRef knowledge graph."""

from collections import deque
from pathlib import Path

from app.domain.entity import Entity, EntityType, Identifier
from app.domain.graph import Neighborhood
from app.domain.relationship import (
    Dataset,
    EntityId,
    Relationship,
    RelationshipType,
)
from app.sources.client import SparqlQueryError
from app.sources.idref.sparql import IDREF_ENDPOINT, IdRefSparqlClient

# ── SPARQL templates (loaded once at module import) ────────────────────

_QUERIES = Path(__file__).resolve().parent.parent / "sources" / "idref" / "queries"

_ENTITY_QUERIES = {
    EntityType.PERSON: (_QUERIES / "person.sparql").read_text(),
    EntityType.ORGANIZATION: (_QUERIES / "organization.sparql").read_text(),
    EntityType.PUBLICATION: (_QUERIES / "publication.sparql").read_text(),
}

# For PERSON, the entity query (person.sparql) already returns org relationships
# inline via ?org — so we don't need a separate query for person→org edges.
# This dict maps which entity types have inline relationships in their entity query.
_INLINE_RELATIONS: dict[EntityType, tuple[EntityType, str]] = {
    EntityType.PERSON: (EntityType.ORGANIZATION, "org"),
}

# Additional relationship queries needed beyond what the entity query provides.
_ADDITIONAL_RELATIONS: dict[EntityType, list[tuple[EntityType, str, str]]] = {
    EntityType.PERSON: [
        (
            EntityType.PUBLICATION,
            (_QUERIES / "person_contributions.sparql").read_text(),
            "doc",
        ),
    ],
    EntityType.ORGANIZATION: [
        (
            EntityType.PERSON,
            (_QUERIES / "organization_members.sparql").read_text(),
            "person",
        ),
        (
            EntityType.PUBLICATION,
            (_QUERIES / "organization_publications.sparql").read_text(),
            "doc",
        ),
    ],
    EntityType.PUBLICATION: [
        (
            EntityType.PERSON,
            (_QUERIES / "publication_persons.sparql").read_text(),
            "person",
        ),
        (
            EntityType.ORGANIZATION,
            (_QUERIES / "publication_organizations.sparql").read_text(),
            "org",
        ),
    ],
}

_PARAM_NAMES: dict[EntityType, str] = {
    EntityType.PERSON: "$person",
    EntityType.ORGANIZATION: "$organization",
    EntityType.PUBLICATION: "$publication",
}

IDREF_DATASET = Dataset(name="IdRef", endpoint=IDREF_ENDPOINT)


# ── ID normalization ──────────────────────────────────────────────────


def _normalize_id(raw_id: str) -> str:
    """Accept raw PPN or full URI, return full IdRef URI."""
    if raw_id.startswith("http://") or raw_id.startswith("https://"):
        return raw_id
    return f"http://www.idref.fr/{raw_id}/id"


# ── Entity binding parser ─────────────────────────────────────────────


def _parse_entity_bindings(
    entity_type: EntityType, entity_uri: str, bindings: list[dict]
) -> Entity:
    """Parse SPARQL bindings into an Entity graph node."""
    if not bindings:
        raise ValueError(f"No bindings for {entity_type} {entity_uri}")

    if entity_type == EntityType.PERSON:
        name = bindings[0]["name"]["value"]
        return Entity(id=entity_uri, label=name, type=EntityType.PERSON)

    elif entity_type == EntityType.ORGANIZATION:
        name = bindings[0]["name"]["value"]
        return Entity(id=entity_uri, label=name, type=EntityType.ORGANIZATION)

    elif entity_type == EntityType.PUBLICATION:
        title = bindings[0]["title"]["value"]
        identifiers = []
        for b in bindings:
            if "sameAs" in b:
                val = b["sameAs"]["value"]
                if not any(i.value == val for i in identifiers):
                    identifiers.append(Identifier(scheme="owl:sameAs", value=val))
            if "uri" in b:
                val = b["uri"]["value"]
                if not any(i.value == val for i in identifiers):
                    identifiers.append(Identifier(scheme="bibo:uri", value=val))
        return Entity(
            id=entity_uri,
            label=title,
            type=EntityType.PUBLICATION,
            identifiers=identifiers,
        )

    raise ValueError(f"Unknown entity type: {entity_type}")


# ── Edge normalization ────────────────────────────────────────────────


def _normalize_edge(
    source_id: str,
    source_type: EntityType,
    target_id: str,
    target_type: EntityType,
) -> Relationship:
    """Create a Relationship with consistent semantic direction.

    Edge direction is always: Person → Org, Person → Pub, Org → Pub.
    This ensures the same edge is deduplicated regardless of which node
    discovers it first.
    """
    if source_type == EntityType.PERSON and target_type == EntityType.ORGANIZATION:
        return Relationship(
            source=EntityId(source_id),
            target=EntityId(target_id),
            type=RelationshipType.AFFILIATED_WITH,
            source_dataset=IDREF_DATASET,
        )
    if source_type == EntityType.ORGANIZATION and target_type == EntityType.PERSON:
        return Relationship(
            source=EntityId(target_id),
            target=EntityId(source_id),
            type=RelationshipType.AFFILIATED_WITH,
            source_dataset=IDREF_DATASET,
        )
    if source_type == EntityType.PERSON and target_type == EntityType.PUBLICATION:
        return Relationship(
            source=EntityId(source_id),
            target=EntityId(target_id),
            type=RelationshipType.AUTHOR_OF,
            source_dataset=IDREF_DATASET,
        )
    if source_type == EntityType.PUBLICATION and target_type == EntityType.PERSON:
        return Relationship(
            source=EntityId(target_id),
            target=EntityId(source_id),
            type=RelationshipType.AUTHOR_OF,
            source_dataset=IDREF_DATASET,
        )
    if source_type == EntityType.ORGANIZATION and target_type == EntityType.PUBLICATION:
        return Relationship(
            source=EntityId(source_id),
            target=EntityId(target_id),
            type=RelationshipType.PRODUCED,
            source_dataset=IDREF_DATASET,
        )
    if source_type == EntityType.PUBLICATION and target_type == EntityType.ORGANIZATION:
        return Relationship(
            source=EntityId(target_id),
            target=EntityId(source_id),
            type=RelationshipType.PRODUCED,
            source_dataset=IDREF_DATASET,
        )
    raise ValueError(f"Unknown edge: {source_type} → {target_type}")


# ── Neighbor extraction ───────────────────────────────────────────────


def _extract_neighbor_ids(bindings: list[dict], binding_key: str) -> set[str]:
    """Extract unique neighbor URIs from relationship query bindings."""
    ids: set[str] = set()
    for b in bindings:
        if binding_key in b:
            ids.add(b[binding_key]["value"])
    return ids


# ── BFS Engine ────────────────────────────────────────────────────────


class GraphTraverser:
    """Breadth-first graph traversal over the IdRef knowledge graph.

    Starting from a root entity, explores relationships up to a given
    depth, collecting nodes and edges. Deduplicates visited entities
    and normalizes edge direction.
    """

    def __init__(self, client: IdRefSparqlClient):
        self._client = client

    async def traverse(
        self,
        root_id: str,
        root_type: EntityType,
        max_depth: int,
        max_nodes: int,
    ) -> Neighborhood:
        """BFS traversal returning a Neighborhood of nodes and edges."""
        root_uri = _normalize_id(root_id)

        visited: set[str] = {root_uri}
        nodes: dict[str, Entity] = {}
        edges: dict[tuple, Relationship] = {}
        frontier: deque[tuple[str, EntityType, int]] = deque([(root_uri, root_type, 0)])

        while frontier:
            current_id, current_type, current_depth = frontier.popleft()

            # Skip if already fetched (discovered via another path)
            if current_id in nodes:
                continue

            # ── Fetch entity info ──────────────────────────────────

            query = _ENTITY_QUERIES[current_type].replace(
                _PARAM_NAMES[current_type], f"<{current_id}>"
            )
            try:
                result = await self._client.cached_query(query)
                bindings = result.get("results", {}).get("bindings", [])
                entity = _parse_entity_bindings(current_type, current_id, bindings)
            except (SparqlQueryError, KeyError, ValueError):
                continue  # Skip entities that fail to resolve

            nodes[current_id] = entity

            if len(nodes) >= max_nodes:
                break

            # ── Inline relationships (from the entity query) ───────

            if current_type in _INLINE_RELATIONS:
                neighbor_type, binding_key = _INLINE_RELATIONS[current_type]
                neighbor_ids = _extract_neighbor_ids(bindings, binding_key)
                for neighbor_id in neighbor_ids:
                    edge = _normalize_edge(
                        current_id, current_type, neighbor_id, neighbor_type
                    )
                    edges[(edge.source, edge.target, edge.type)] = edge
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        if len(nodes) < max_nodes:
                            frontier.append(
                                (neighbor_id, neighbor_type, current_depth + 1)
                            )

            # ── Additional relationship queries ────────────────────

            if current_depth < max_depth and current_type in _ADDITIONAL_RELATIONS:
                for neighbor_type, rel_query, binding_key in _ADDITIONAL_RELATIONS[
                    current_type
                ]:
                    try:
                        rq = rel_query.replace(
                            _PARAM_NAMES[current_type], f"<{current_id}>"
                        )
                        result = await self._client.cached_query(rq)
                        rel_bindings = result.get("results", {}).get("bindings", [])
                    except SparqlQueryError:
                        continue

                    neighbor_ids = _extract_neighbor_ids(rel_bindings, binding_key)
                    for neighbor_id in neighbor_ids:
                        edge = _normalize_edge(
                            current_id, current_type, neighbor_id, neighbor_type
                        )
                        edges[(edge.source, edge.target, edge.type)] = edge
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            if len(nodes) < max_nodes:
                                frontier.append(
                                    (neighbor_id, neighbor_type, current_depth + 1)
                                )

        # ── Validate root was resolved ─────────────────────────────

        if root_uri not in nodes:
            raise ValueError(f"Could not resolve root entity: {root_uri}")

        return Neighborhood(
            center=nodes[root_uri],
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )
