"""Graph traversal engine — BFS over the IdRef knowledge graph."""

import asyncio
from collections import deque
from dataclasses import dataclass

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


@dataclass(frozen=True)
class RelationSpec:
    neighbor_type: EntityType
    query: str
    binding_key: str
    role_key: str | None
    role_fallback: str | None


# Additional relationship queries needed beyond the entity query.
_ADDITIONAL_RELATIONS: dict[EntityType, list[RelationSpec]] = {
    EntityType.PERSON: [
        RelationSpec(
            EntityType.PUBLICATION, PERSON_CONTRIBUTIONS, "doc", "role", "authorOf"
        ),
        RelationSpec(
            EntityType.PERSON, PERSON_CONTRIBUTIONS, "author", None, "coAuthorOf"
        ),
    ],
    EntityType.ORGANIZATION: [
        RelationSpec(
            EntityType.PERSON, ORGANIZATION_MEMBERS, "person", None, "memberOf"
        ),
        RelationSpec(
            EntityType.PUBLICATION, ORGANIZATION_PUBLICATIONS, "doc", None, "produced"
        ),
        # Also extract authors linked to the organization's publications
        RelationSpec(
            EntityType.PERSON,
            ORGANIZATION_PUBLICATIONS,
            "author",
            None,
            "affiliatedAuthor",
        ),
    ],
    EntityType.PUBLICATION: [
        RelationSpec(
            EntityType.PERSON, PUBLICATION_PERSONS, "person", "person_role", None
        ),
        RelationSpec(
            EntityType.ORGANIZATION, PUBLICATION_ORGANIZATIONS, "org", "org_role", None
        ),
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
        doi = bindings[0].get("doi", {}).get("value")
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
            doi=doi,
            identifiers=dedup_identifiers(identifiers),
        )

    raise ValueError(f"Unknown entity type: {entity_type}")


def _extract_neighbor_ids(
    bindings: list[dict], binding_key: str, role_key: str | None = None
) -> dict[str, str | None]:
    """Extract unique neighbor URIs with optional role from bindings.

    Returns dict mapping neighbor_id → role (or None if no role key).
    """
    ids: dict[str, str | None] = {}
    for b in bindings:
        if binding_key in b:
            nid = b[binding_key]["value"]
            if nid not in ids:
                role = b.get(role_key, {}).get("value") if role_key else None
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


@dataclass(frozen=True)
class TraversalState:
    """Serializable resume state for a truncated traversal."""

    root_id: str
    root_type: EntityType
    max_depth: int
    visited: set[str]
    edge_keys: set[tuple[str, str, str]]
    frontier: list[dict]

    def to_dict(self) -> dict:
        """Serialize to JSON-safe primitives (deterministic ordering)."""
        return {
            "root_id": self.root_id,
            "root_type": self.root_type.value,
            "max_depth": self.max_depth,
            "visited": sorted(self.visited),
            "edge_keys": [list(key) for key in sorted(self.edge_keys)],
            "frontier": self.frontier,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TraversalState":
        """Reconstruct a state from its serialized form."""
        return cls(
            root_id=d["root_id"],
            root_type=EntityType(d["root_type"]),
            max_depth=d["max_depth"],
            visited=set(d["visited"]),
            edge_keys={tuple(key) for key in d["edge_keys"]},
            frontier=d["frontier"],
        )


@dataclass(frozen=True)
class TraversalResult:
    """Outcome of one traversal chunk."""

    neighborhood: Neighborhood
    next_state: TraversalState | None


class GraphTraverser:
    """Breadth-first graph traversal over the IdRef knowledge graph."""

    def __init__(self, client: IdRefSparqlClient):
        self._client = client
        # The IdRef client's cache session (AsyncSession) is not safe for
        # concurrent use, so serialize access when batching relation queries.
        self._cache_lock = asyncio.Lock()

    async def traverse(
        self,
        root_id: str,
        root_type: EntityType,
        max_depth: int,
        max_nodes: int,
        max_edges: int,
        state: TraversalState | None = None,
    ) -> TraversalResult:
        """BFS traversal returning a single chunk of the neighborhood.

        ``max_nodes`` and ``max_edges`` bound the NEW nodes and edges returned
        in this chunk. When a cap forces a relationship (or its neighbor) to be
        skipped, the remainder is captured in ``next_state`` so the caller can
        resume with a follow-up request.
        """
        if state is not None:
            root_id = state.root_id
            root_type = state.root_type
            max_depth = state.max_depth

        root_uri = normalize_idref_id(root_id)

        # ── Local state for this chunk ─────────────────────────
        resolved: set[str] = set()
        edge_keys: set[tuple[str, str, str]] = set()
        discovered: set[str] = set()
        frontier: deque[tuple[str, EntityType, int, list[list[str]]]]

        if state is None:
            discovered = {root_uri}
            frontier = deque([(root_uri, root_type, 0, [])])
        else:
            resolved = set(state.visited)
            edge_keys = set(state.edge_keys)
            frontier = deque(
                (e["id"], EntityType(e["type"]), e["depth"], e["incoming"])
                for e in state.frontier
            )
            discovered = resolved | {e["id"] for e in state.frontier}

        nodes: dict[str, Entity] = {}
        new_edges: dict[tuple, Relationship] = {}
        edges_added = 0
        committed = 0  # NEW node slots reserved this chunk (resolved + pending)
        pending_new: set[str] = set()  # new neighbors enqueued but unresolved
        spill: list[tuple] = []

        def _try_add_edge(source_id: str, target_id: str, edge_type: str) -> bool:
            nonlocal edges_added
            key = (source_id, target_id, edge_type)
            if key in edge_keys:
                return True
            if edges_added >= max_edges:
                return False
            edge = Relationship(
                source=EntityId(source_id),
                target=EntityId(target_id),
                type=edge_type,
                source_dataset=IDREF_DATASET,
            )
            new_edges[key] = edge
            edge_keys.add(key)
            edges_added += 1
            return True

        def add_edge_and_enqueue(
            source_id: str,
            neighbor_id: str,
            neighbor_type: EntityType,
            edge_type: str,
            depth: int,
        ) -> None:
            nonlocal committed
            if (source_id, neighbor_id, edge_type) in edge_keys:
                return
            is_new = neighbor_id not in discovered
            if is_new and committed >= max_nodes:
                spill.append(
                    (source_id, neighbor_id, neighbor_type, edge_type, depth + 1)
                )
                return
            if not _try_add_edge(source_id, neighbor_id, edge_type):
                spill.append(
                    (source_id, neighbor_id, neighbor_type, edge_type, depth + 1)
                )
                return
            if is_new:
                discovered.add(neighbor_id)
                pending_new.add(neighbor_id)
                committed += 1
                frontier.append((neighbor_id, neighbor_type, depth + 1, []))

        while frontier:
            current_id, current_type, current_depth, incoming = frontier.popleft()

            # Emit deferred incoming edges from a prior chunk before the node.
            if incoming:
                emitted_all = True
                for i, (src, et) in enumerate(incoming):
                    if not _try_add_edge(src, current_id, et):
                        for rest_src, rest_et in incoming[i:]:
                            spill.append(
                                (
                                    rest_src,
                                    current_id,
                                    current_type,
                                    rest_et,
                                    current_depth,
                                )
                            )
                        if current_id not in resolved:
                            spill.append(
                                (None, current_id, current_type, None, current_depth)
                            )
                        emitted_all = False
                        break
                if not emitted_all:
                    continue

            if current_id in resolved:
                continue

            # A resume-pending node consumes a NEW node slot when resolved.
            if current_id not in pending_new:
                if committed >= max_nodes:
                    spill.append((None, current_id, current_type, None, current_depth))
                    continue
                committed += 1

            query = _ENTITY_QUERIES[current_type].replace(
                _PARAM_NAMES[current_type], f"<{current_id}>"
            )
            try:
                result = await self._client.cached_query(query)
                bindings = result.get("results", {}).get("bindings", [])
                entity = _parse_entity_bindings(current_type, current_id, bindings)
            except (SparqlQueryError, KeyError, ValueError):
                resolved.add(current_id)
                pending_new.discard(current_id)
                continue

            nodes[current_id] = entity
            resolved.add(current_id)
            pending_new.discard(current_id)
            expand = current_depth < max_depth

            # ── Inline relationships ────────────────────────────
            if expand and current_type in _INLINE_RELATIONS:
                neighbor_type, binding_key, role_fallback = _INLINE_RELATIONS[
                    current_type
                ]
                neighbor_ids = _extract_neighbor_ids(bindings, binding_key)
                for neighbor_id, role in neighbor_ids.items():
                    if neighbor_id == current_id:
                        continue
                    edge_role = _infer_edge_role(
                        current_type, neighbor_type, role_fallback, role
                    )
                    add_edge_and_enqueue(
                        current_id, neighbor_id, neighbor_type, edge_role, current_depth
                    )

            # ── Additional relationship queries ─────────────────
            if expand and current_type in _ADDITIONAL_RELATIONS:
                by_query: dict[str, list[RelationSpec]] = {}
                for spec in _ADDITIONAL_RELATIONS[current_type]:
                    rq = spec.query.replace(
                        _PARAM_NAMES[current_type], f"<{current_id}>"
                    )
                    by_query.setdefault(rq, []).append(spec)

                async def fetch_relations(rq: str) -> tuple[str, list[dict]]:
                    try:
                        async with self._cache_lock:
                            result = await self._client.cached_query(rq)
                        return rq, result.get("results", {}).get("bindings", [])
                    except SparqlQueryError:
                        return rq, []

                fetched = await asyncio.gather(
                    *(fetch_relations(rq) for rq in by_query)
                )
                rel_results = dict(fetched)

                for rq, specs in by_query.items():
                    rel_bindings = rel_results[rq]
                    for spec in specs:
                        neighbor_ids = _extract_neighbor_ids(
                            rel_bindings, spec.binding_key, spec.role_key
                        )
                        for neighbor_id, role in neighbor_ids.items():
                            if neighbor_id == current_id:
                                continue
                            edge_role = _infer_edge_role(
                                current_type,
                                spec.neighbor_type,
                                spec.role_fallback or "relatedTo",
                                role,
                            )
                            add_edge_and_enqueue(
                                current_id,
                                neighbor_id,
                                spec.neighbor_type,
                                edge_role,
                                current_depth,
                            )

        # ── Center resolution ──────────────────────────────────
        center = nodes.get(root_uri)
        if center is None and state is not None:
            # On resume the root is not in the frontier, so fetch it again
            # solely to serve as the response center.
            query = _ENTITY_QUERIES[root_type].replace(
                _PARAM_NAMES[root_type], f"<{root_uri}>"
            )
            try:
                result = await self._client.cached_query(query)
                bindings = result.get("results", {}).get("bindings", [])
                center = _parse_entity_bindings(root_type, root_uri, bindings)
            except (SparqlQueryError, KeyError, ValueError):
                center = None

        if center is None:
            raise ValueError(f"Root entity not found: {root_id}")

        # ── Next-chunk resume state ─────────────────────────────
        next_state: TraversalState | None = None
        if spill:
            frontier_map: dict[tuple[str, str], dict] = {}
            for src, nid, ntype, et, ndepth in spill:
                key = (nid, ntype.value)
                entry = frontier_map.setdefault(
                    key,
                    {
                        "id": nid,
                        "type": ntype.value,
                        "depth": ndepth,
                        "incoming": [],
                    },
                )
                if src is not None and et is not None:
                    entry["incoming"].append([src, et])
            next_state = TraversalState(
                root_id=root_id,
                root_type=root_type,
                max_depth=max_depth,
                visited=resolved,
                edge_keys=edge_keys,
                frontier=list(frontier_map.values()),
            )

        return TraversalResult(
            neighborhood=Neighborhood(
                center=center,
                nodes=list(nodes.values()),
                edges=list(new_edges.values()),
                truncated=bool(spill),
                continuation_id=None,
            ),
            next_state=next_state,
        )
