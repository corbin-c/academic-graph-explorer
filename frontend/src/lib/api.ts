// ---- Types ----

export interface SearchResult {
  id: string
  name: string
  type: "person" | "organization"
}

export interface OrganizationRef {
  id: string
  name: string
}

export interface PersonDetail {
  id: string
  name: string
  note: string | null
  organizations: OrganizationRef[]
}

export interface OrganizationDetail {
  id: string
  name: string
  note: string | null
}

export type EntityDetail = PersonDetail | OrganizationDetail

export interface Identifier {
  scheme: string
  value: string
}

export interface GraphEntity {
  id: string
  label: string
  type: string
  identifiers: Identifier[]
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  source_dataset: {
    name: string
    endpoint: string | null
  }
}

export interface Neighborhood {
  center: GraphEntity
  nodes: GraphEntity[]
  edges: GraphEdge[]
}

// ---- API functions ----

export async function searchApi(query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query })
  const response = await fetch(`/api/search/?${params}`)
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchEntityDetail(
  id: string,
  type: "person" | "organization"
): Promise<EntityDetail> {
  const endpoint = type === "person" ? "person" : "organization"
  const response = await fetch(`/api/${endpoint}/${encodeURIComponent(id)}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch ${type} details: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchGraphTraversal(
  root: string,
  type: "person" | "organization",
  depth: number = 1,
  limit: number = 100
): Promise<Neighborhood> {
  const params = new URLSearchParams({
    root,
    type,
    depth: String(depth),
    limit: String(limit),
  })
  const response = await fetch(`/api/graph/?${params}`)
  if (!response.ok) {
    throw new Error(`Graph traversal failed: ${response.statusText}`)
  }
  return response.json()
}
