# Graph Traversal — Analysis

## 1. Scope & entry points

| Layer         | File                                                    | Role                                                      |
| ------------- | ------------------------------------------------------- | --------------------------------------------------------- |
| Endpoint      | `backend/app/api/graph.py`                                | `GET /api/graph/` with `root`, `type`, `depth` (default 2, `1..10`), `max_nodes` (default 100), `max_edges` (default 200) |
| Engine        | `backend/app/services/graph_traversal.py`                 | `GraphTraverser.traverse()` — BFS                           |
| Domain        | `backend/app/domain/graph.py`, `entity.py`, `relationship.py` | `Neighborhood`, `Entity` hierarchy, `Relationship`              |
| Source client | `backend/app/sources/client.py`, `sources/idref/sparql.py`  | `HttpSparqlClient` (retry + cache), `IdRefSparqlClient`       |
| Queries       | `backend/app/sources/idref/queries/*.sparql`              | 8 SPARQL templates                                        |

## 2. Algorithm (`GraphTraverser.traverse`)

Breadth-first search over the IdRef SPARQL endpoint:

1. `normalize_idref_id(root_id)` → canonical URI (`normalize.py:4`).
2. Seed `visited={root}`, `nodes={}`, `edges={}`, frontier deque `[(root, root_type, 0)]`.
3. Pop `(id, type, depth)`.
4. Fetch entity via `_ENTITY_QUERIES[type]`; on `SparqlQueryError`/`KeyError`/`ValueError`, `continue` (silent degradation).
5. Compute `expand = current_depth < max_depth`; if `expand`, expand neighbors in two tiers:
   - **Inline relations** (`_INLINE_RELATIONS`, only `person → org` via `?org`).
   - **Additional relations** (`_ADDITIONAL_RELATIONS`) — fetched concurrently via `asyncio.gather`, deduped by final query string.
6. New neighbors are marked `visited` at enqueue time and pushed at `current_depth + 1`; self-loops (`neighbor_id == current_id`) are skipped.
7. Edges dedup on `(source, target, type)`; nodes dedup by id.
8. Root unresolved after BFS → `ValueError` → HTTP 404.
9. Size caps enforced at discovery: a new neighbor is skipped (and `truncated` set) when `len(visited) >= max_nodes`; any edge is skipped (and `truncated` set) when `len(edges) >= max_edges`.

## 3. Relationship expansion tiers

`_INLINE_RELATIONS` (depth-gated, no role key):
- `person → organization` ("affiliatedWith", from `?org` in `person.sparql`)

`_ADDITIONAL_RELATIONS` is a `dict[EntityType, list[RelationSpec]]`, where `RelationSpec(neighbor_type, query, binding_key, role_key, role_fallback, source_key=None)`:

| Source       | Neighbor     | Query template                   | binding_key   | role_key         | fallback role      | source_key |
| ------------ | ------------ | -------------------------------- | ------------- | ---------------- | ------------------ | ---------- |
| person       | publication  | `person_contributions.sparql`      | `doc`         | `role`           | `authorOf`           | —          |
| person       | person       | `person_contributions.sparql`      | `contributor` | `contributor_role` | `contributor`     | `doc`      |
| organization | person       | `organization_members.sparql`      | `person`      | —                | `memberOf`           | —          |
| organization | publication  | `organization_publications.sparql` | `doc`         | —                | `produced`           | —          |
| organization | person       | `organization_publications.sparql` | `contributor` | `contributor_role` | `contributor`     | `doc`      |
| publication  | person       | `publication_persons.sparql`       | `person`      | `person_role`    | `relatedTo` (fallback None) | — |
| publication  | organization | `publication_organizations.sparql` | `org`         | `org_role`       | `relatedTo` (fallback None) | — |

Role resolution: `_extract_neighbor_ids(bindings, binding_key, role_key)` uses the explicit `role_key` when provided, otherwise `_infer_edge_role` falls back to `role_fallback` (or `relatedTo` when None).

Co-authorship and org affiliation are expanded **through the publication**. The merged contributor queries (`person_contributions.sparql`, `organization_publications.sparql`) return `?contributor`/`?contributor_role` alongside `?doc`, so a person's or organization's publications link onward to their co-authors via `publication → person` edges whose source is the `?doc` binding (the `source_key` field). The collapsed `coAuthorOf` and `affiliatedAuthor` shortcuts are gone — the publication now sits in between.

A `source_key` spec emits its edge from a *different* binding than the current node. `_extract_pairs(bindings, source_key, binding_key, role_key)` returns `[(source_id, target_id, role)]` deduped by `(source, target)`; the loop then enqueues `target` (at `current_depth + 2`) and, when `source` was already discovered this chunk, adds the edge immediately — otherwise it defers the edge to `spill` for the next chunk (see §5).

`publication_persons.sparql` runs **only when the publication is the traversal root** (`current_id == root_uri`). A publication reached in the middle of a traversal is skipped, because its persons are already supplied by the contributor query of the entity that led to it — avoiding duplicate `publication → person` edges from two sources.

## 4. Depth semantics

A single `expand = current_depth < max_depth` gate now applies **uniformly** to both tiers:

- Nodes at depths `0..N-1` are expanded; nodes sitting exactly at depth `N` have their entity resolved (so they render as leaves) but are not expanded further.
- Inline relations no longer leak past the bound (previously they expanded unconditionally).

Concrete effect for `depth=1` on a person root: the person's org (inline) and publications (additional) are added, but the org's/publication's own neighbors are not expanded.

## 5. Size bounds & truncation

The traversal also accepts `max_nodes` (max discovered nodes) and `max_edges` (max returned edges), enforced by a single `add_edge_and_enqueue` helper shared by both expansion tiers:

- **Node cap** — for a *new* neighbor, if `len(visited) >= max_nodes`, both the edge and the enqueue are skipped (avoiding dangling edges to unresolved nodes); `truncated` is set.
- **Edge cap** — if `len(edges) >= max_edges`, the edge (and its neighbor) is skipped; `truncated` is set.

Invariants: capping `visited` guarantees the final `len(nodes) <= max_nodes`; capping `edges` guarantees `len(edges) <= max_edges`. The root is always resolved (`max_nodes >= 1`). `Neighborhood.truncated` (default `False`) signals a partial subgraph. Defaults: `max_nodes=100`, `max_edges=200`.

**Deferred contributors.** When a `source_key` spec's `source` (the publication) was spilled earlier in the same chunk — i.e. it is not yet in `discovered` — the `publication → contributor` edge is appended to `spill` at `current_depth + 2` instead of being added immediately. On resume, the existing spill/frontier/incoming machinery re-emits it: the publication is resolved in a later chunk, and its contributor is enqueued with that edge as its incoming edge, so truncated publications still yield their co-author edges in a follow-up chunk. No extra `TraversalState` fields are required.

## 6. Deduplication

- Nodes: `visited` marks entities at enqueue time → each entity is enqueued at most once; `nodes` dict by id dedups output.
- Edges: keyed by `(source, target, type)` → parallel edges with distinct roles preserved; identical duplicates collapsed.
- Self-loops: `neighbor_id == current_id` skipped (the contributor query returns the root person among its own contributors).
- Query dedup: before batching, relation specs are grouped by their final query string, so templates consumed by two specs (`PERSON_CONTRIBUTIONS` for `doc`+`contributor`; `ORGANIZATION_PUBLICATIONS` for `doc`+`contributor`) are fetched once per node.

## 7. Error handling & concurrency

- Per-node entity fetch failure → node silently dropped, traversal continues.
- Per-relation query failure → that query's specs get empty bindings, traversal continues.
- Root unresolved → `ValueError` → 404 (`graph.py:45-46`).
- Endpoint transport errors → retried 3× with exponential backoff, then `SparqlQueryError` → 502.
- `GraphTraverser` holds an `asyncio.Lock` (`_cache_lock`) held across each `cached_query`, because the injected `AsyncSession` is not safe for concurrent use.

## 8. Resolved issues

The following latent issues identified in the first pass have been fixed:

1. **Depth bound inconsistency** — inline relations bypassed `max_depth`. Now gated by the uniform `expand` check.
2. **Role loss** — `_extract_neighbor_ids` auto-derived `{binding_key}_role`, missing `?role` in `person_contributions.sparql`. Now uses explicit `role_key` per `RelationSpec`; person→publication edges capture the real `"author"` role.
3. **Co-author shortcut removed** — `coAuthorOf` (person→person) was replaced with `publication → person` edges derived from the merged contributor query, so co-authorship is expanded through the publication.
4. **Publication DOI dropped** — `_parse_entity_bindings` now reads the `doi` binding into `Publication.doi`.
5. **Misleading edge label removed** — `affiliatedAuthor` (org→person) was likewise replaced with `publication → person` edges; org affiliation is expanded through the publication.
6. **Dead code** — removed unused `_queried_queries` and the redundant `if current_id in nodes: continue` guard.

## 9. Remaining observations

1. **I/O parallelism not fully realized.** Relation queries are dispatched via `asyncio.gather`, but `_cache_lock` serializes the whole `cached_query` (DB read + HTTP + DB write), so HTTP calls remain effectively sequential. True parallelism would require scoping the lock to DB access only, or using a per-query session.
2. **`_infer_edge_role` takes unused `source_type`/`target_type` parameters** — cosmetic; it only uses `fallback` and `role_from_query`.

## 10. API contract

`GET /api/graph/?root=<id|uri>&type=person|organization|publication&depth=<1..10>&max_nodes=<n>&max_edges=<n>&continuation=<id>`

- `depth` default 2; validated `ge=1, le=10` (422 otherwise).
- `type` validated against `EntityType` enum; invalid → 422.
- `max_nodes` default 100; validated `ge=1` (422 otherwise).
- `max_edges` default 200; validated `ge=1` (422 otherwise).
- `continuation` optional; a session id from a prior truncated response. An unknown or expired id → 404.
- Response `Neighborhood { center, nodes[], edges[], truncated, continuation_id }`, nodes serialized via `type` discriminator; `truncated` is `true` when a cap cut the traversal short, and `continuation_id` is set only when a follow-up chunk is available.

## 11. Test coverage (`tests/api/test_graph.py`)

Validation (missing root/type → 422, invalid type → 422, depth 0 → 422), depth-1 (single node; person+inline org), depth-2 (person→publications; dedup; root-not-found 404; SPARQL failure recovery), plus tests for: depth boundary (leaf person's org not expanded), role capture (`author`), DOI population, person depth-2 expanding co-authors through the publication (no `coAuthorOf`), organization depth-2 expanding contributors through the publication (no `affiliatedAuthor`), a publication root still resolving its persons, and a publication reached not-as-root skipping `publication_persons`. Depth-2 mocks disambiguate concurrent requests using exact-bytes `match_content` (pytest-httpx 0.36.2 does not support callable matchers). Truncation tests cover the caps: `test_max_nodes_truncates`, `test_max_edges_truncates`, and `test_within_limits_not_truncated` (asserting the `truncated` flag). Continuation is covered by `TestGraphContinuation`: `test_truncated_response_returns_continuation_id`, `test_continuation_returns_new_nodes_and_edges` (chunks are disjoint), `test_continuation_terminates_when_not_truncated` (chunks stitch into the full graph with no duplicate node/edge keys), `test_truncated_publication_contributors_recovered_after_resume` (a spilled publication's co-author edges arrive in a later chunk), and `test_unknown_continuation_returns_404`.

## 12. Continuation sessions

When a traversal hits its `max_nodes`/`max_edges` caps mid-BFS, the endpoint returns a partial `Neighborhood` with `truncated: true` and a `continuation_id`. The client replays that id to fetch the next chunk.

- **Query param** — `GET /api/graph/?continuation=<id>` resumes a prior truncated traversal. The id is validated against the `traversal_sessions` table; an unknown or expired id yields 404.
- **Response fields** — `Neighborhood.truncated: bool` signals a partial subgraph; `Neighborhood.continuation_id: string | null` carries the resume token, non-null only when another chunk remains.
- **Per-chunk semantics** — `max_nodes`/`max_edges` bound the NEW nodes and edges returned in each chunk, not the cumulative total. Each chunk re-resolves the root to serve as `center` and only emits nodes/edges not already returned, so chunks can be stitched together without duplicates.
- **Server state** — the resume state (visited set, edge keys, frontier) is serialized to JSON and stored in the `TraversalSession` table (`state_json` column) with a 900s TTL (`ttl_seconds`). `create_session` mints a `uuid4().hex` id; `update_session` replaces the state after each chunk; `load_session` returns `None` for missing or expired rows.
- **Client behavior** — the graph page auto-continues up to `AUTO_BATCH_LIMIT = 3` extra chunks automatically after the initial load; beyond that, a "Load more" button appears (only while `truncated && continuation_id`). Merged chunks are deduped by node id and by `(source, target, type)` edge key. The frontend's default depth is 2 (when no `depth` search param is present), so an initial person/org load already shows the publication hop and the co-authors on the far side of it.
