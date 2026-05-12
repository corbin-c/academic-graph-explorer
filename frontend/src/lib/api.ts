import createClient from "openapi-fetch"
import type { paths, components } from "./api-types"

// ── Typed API client ──────────────────────────────────────────────────

export const client = createClient<paths>({ baseUrl: "" })

// ── Re-exported types from OpenAPI schema ─────────────────────────────

export type SearchResult = components["schemas"]["SearchResult"]
export type Person = components["schemas"]["Person"]
export type Organization = components["schemas"]["Organization"]
export type Publication = components["schemas"]["Publication"]
export type Identifier = components["schemas"]["Identifier"]
export type EntityDetail = Person | Organization | Publication
export type GraphEntity = Person | Organization | Publication
export type GraphEdge = components["schemas"]["Relationship"]
export type Neighborhood = components["schemas"]["Neighborhood"]

// ── API functions ─────────────────────────────────────────────────────

/** Search for persons and organizations in IdRef. */
export async function searchApi(q: string): Promise<SearchResult[]> {
  const { data, error } = await client.GET("/api/search/", {
    params: { query: { q } },
  })
  if (error) throw new Error("Search failed", { cause: error })
  return data ?? []
}

/** Get detailed information for an entity by ID and type. */
export async function fetchEntityDetail(
  id: string,
  type: string,
): Promise<EntityDetail> {
  if (type === "person") {
    const { data, error } = await client.GET("/api/person/{person_id}", {
      params: { path: { person_id: id } },
    })
    if (error) throw new Error("Failed to fetch person details", { cause: error })
    return data!
  }

  if (type === "organization") {
    const { data, error } = await client.GET(
      "/api/organization/{organization_id}",
      {
        params: { path: { organization_id: id } },
      },
    )
    if (error)
      throw new Error("Failed to fetch organization details", { cause: error })
    return data!
  }

  if (type === "publication") {
    const { data, error } = await client.GET(
      "/api/publication/{publication_id}",
      {
        params: { path: { publication_id: id } },
      },
    )
    if (error)
      throw new Error("Failed to fetch publication details", { cause: error })
    return data!
  }

  throw new Error(`Unknown entity type: ${type}`)
}

/** Traverse the knowledge graph from a root entity. */
export async function fetchGraphTraversal(
  root: string,
  type: string,
  depth: number = 2,
  limit: number = 100,
): Promise<Neighborhood> {
  const { data, error } = await client.GET("/api/graph/", {
    params: { query: { root, type, depth, limit } },
  })
  if (error) throw new Error("Graph traversal failed", { cause: error })
  return data!
}
