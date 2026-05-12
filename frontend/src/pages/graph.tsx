import { useState, useEffect, useMemo } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { fetchGraphTraversal, type Neighborhood, type GraphEntity } from "@/lib/api"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
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
      const newNh = await fetchGraphTraversal(nodeId, type, 1, 50)
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
    </div>
  )
}
