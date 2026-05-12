import { useState, useEffect, useMemo } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { ArrowLeft, Search } from "lucide-react"
import { fetchGraphTraversal, type Neighborhood, type GraphEntity } from "@/lib/api"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { GraphCanvas } from "@/components/graph/graph-canvas"
import { GraphSidebar } from "@/components/graph/graph-sidebar"

export function GraphPage() {
  const { entityId } = useParams<{ entityId: string }>()
  const [searchParams] = useSearchParams()
  const entityType = (searchParams.get("type") ?? "person") as
    | "person"
    | "organization"

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [neighborhood, setNeighborhood] = useState<Neighborhood | undefined>()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set())
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [expandDepth, setExpandDepth] = useState(2)

  const matchCount = useMemo(() => {
    if (!searchQuery.trim() || !neighborhood) return 0
    const q = searchQuery.toLowerCase()
    return neighborhood.nodes.filter((n) => n.label.toLowerCase().includes(q)).length
  }, [searchQuery, neighborhood])

  // Initial graph load
  useEffect(() => {
    if (!entityId) return
    setIsLoading(true)
    setError(null)
    fetchGraphTraversal(entityId, entityType)
      .then(setNeighborhood)
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false))
  }, [entityId, entityType])

  // Expand: fetch neighborhood around selected node, merge into current
  async function handleExpand(nodeId: string, type: string) {
    setExpandingNodeId(nodeId)
    try {
      const newNh = await fetchGraphTraversal(nodeId, type, expandDepth)
      setNeighborhood((prev) => {
        if (!prev) return newNh
        const existingIds = new Set(prev.nodes.map((n) => n.id))
        const edgeKey = (e: { source: string; target: string }) =>
          `${e.source}→${e.target}`
        const existingEdgeKeys = new Set(prev.edges.map(edgeKey))
        return {
          center: prev.center,
          nodes: [
            ...prev.nodes,
            ...newNh.nodes.filter((n) => !existingIds.has(n.id)),
          ],
          edges: [
            ...prev.edges,
            ...newNh.edges.filter((e) => !existingEdgeKeys.has(edgeKey(e))),
          ],
        }
      })
      setExpandedNodeIds((prev) => new Set(prev).add(nodeId))
    } catch {
      // Expansion errors are non-critical — silently ignore
    } finally {
      setExpandingNodeId(null)
    }
  }

  const selectedNode = useMemo<GraphEntity | undefined>(() => {
    if (!neighborhood || !selectedNodeId) return undefined
    return neighborhood.nodes.find((n) => n.id === selectedNodeId)
  }, [neighborhood, selectedNodeId])

  function handleSelectNode(nodeId: string | null) {
    setSelectedNodeId(nodeId)
  }

  return (
    <div className="flex h-svh flex-col">
      {/* Top bar */}
      <header className="flex shrink-0 items-center gap-3 border-b border-border px-4 py-2">
        <Link
          to="/"
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back
        </Link>
        <span className="truncate text-sm text-muted-foreground">
          Graph · {neighborhood?.center.label ?? "..."}
        </span>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Graph canvas */}
        <div className="relative flex-1">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background">
              <div className="space-y-4 text-center">
                <Skeleton className="mx-auto h-64 w-64 rounded-full" />
                <p className="text-sm text-muted-foreground">
                  Building graph...
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background">
              <div className="space-y-2 text-center">
                <p className="text-destructive">Failed to load graph.</p>
                <p className="text-sm text-muted-foreground">{error.message}</p>
                <Link
                  to="/"
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-2")}
                >
                  Back to search
                </Link>
              </div>
            </div>
          )}

          {neighborhood && (
            <GraphCanvas
              neighborhood={neighborhood}
              selectedNodeId={selectedNodeId}
              onSelectNode={handleSelectNode}
              searchQuery={searchQuery}
            />
          )}
        </div>

        {/* Sidebar */}
        {selectedNode && neighborhood && (
          <GraphSidebar
            neighborhood={neighborhood}
            selectedNode={selectedNode}
            onSelectNode={handleSelectNode}
            onClose={() => setSelectedNodeId(null)}
            expandedNodeIds={expandedNodeIds}
            expandingNodeId={expandingNodeId}
            onExpand={handleExpand}
          />
        )}
      </div>

      {/* Bottom bar — search + depth */}
      {neighborhood && (
        <footer className="flex shrink-0 items-center gap-2 border-t border-border px-4 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 flex-1 border-0 bg-transparent text-sm focus-visible:ring-0"
          />
          {searchQuery && matchCount > 0 && (
            <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
              {matchCount} match{matchCount !== 1 ? "es" : ""}
            </span>
          )}
          <span className="shrink-0 text-xs text-muted-foreground">Depth:</span>
          <select
            value={expandDepth}
            onChange={(e) => setExpandDepth(Number(e.target.value))}
            className="h-8 shrink-0 rounded-none border border-border bg-background px-2 text-xs"
          >
            {[1, 2, 3, 4, 5].map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </footer>
      )}
    </div>
  )
}
