export interface SearchResult {
  id: string
  name: string
  type: "person" | "organization"
}

export async function searchApi(query: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query })
  const response = await fetch(`/api/search/?${params}`)
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`)
  }
  return response.json()
}
