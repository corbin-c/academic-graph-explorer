import { useState, useEffect, useMemo, useCallback } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { ArrowLeft, Search } from "lucide-react"
import {
  fetchGraphTraversal,
  type Neighborhood,
  type GraphEntity,
  type GraphEdge,
} from "@/lib/api"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { GraphCanvas } from "@/components/graph/graph-canvas"
import { GraphSidebar } from "@/components/graph/graph-sidebar"

// Max number of continuation chunks fetched automatically before the user
// must click "Load more".
const AUTO_BATCH_LIMIT = 5

/** Merge two neighborhoods, deduping nodes by id and edges by (source, target, type).
 *  `prev.truncated` and `prev.continuation_id` are preserved as-is — the per-node
 *  continuation map is the source of truth for pagination. */
function mergeNeighborhood(
  prev: Neighborhood,
  next: Neighborhood
): Neighborhood {
  const existingIds = new Set(prev.nodes.map((n) => n.id))
  const edgeKey = (e: GraphEdge) => `${e.source}→${e.target}→${e.type}`
  const existingEdgeKeys = new Set(prev.edges.map(edgeKey))
  return {
    center: prev.center,
    nodes: [...prev.nodes, ...next.nodes.filter((n) => !existingIds.has(n.id))],
    edges: [
      ...prev.edges,
      ...next.edges.filter((e) => !existingEdgeKeys.has(edgeKey(e))),
    ],
    truncated: prev.truncated,
    continuation_id: prev.continuation_id,
  }
}

export function GraphPage() {
  const { entityId } = useParams<{ entityId: string }>()
  const [searchParams] = useSearchParams()
  const entityType = (searchParams.get("type") ?? "person") as
    "person" | "organization"

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [neighborhood, setNeighborhood] = useState<Neighborhood | undefined>()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set())
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [expandDepth, setExpandDepth] = useState(
    parseInt(searchParams.get("depth") || "2")
  )
  const [loadingMore, setLoadingMore] = useState(false)
  const [continuations, setContinuations] = useState<Record<string, string>>({})
  const [chunksFetched, setChunksFetched] = useState<Record<string, number>>({})

  const matchCount = useMemo(() => {
    if (!searchQuery.trim() || !neighborhood) return 0
    const q = searchQuery.toLowerCase()
    return neighborhood.nodes.filter((n) => n.label.toLowerCase().includes(q))
      .length
  }, [searchQuery, neighborhood])

  // Active continuation target: the selected node's session if it has one,
  // else the root's. Each entry is { nodeId, token }.
  const activeContinuation = useMemo<{
    nodeId: string
    token: string
  } | null>(() => {
    if (!entityId) return null
    if (selectedNodeId && continuations[selectedNodeId]) {
      return { nodeId: selectedNodeId, token: continuations[selectedNodeId] }
    }
    if (continuations[entityId]) {
      return { nodeId: entityId, token: continuations[entityId] }
    }
    return null
  }, [entityId, selectedNodeId, continuations])

  const activeNodeId = activeContinuation?.nodeId
  const autoFetched = activeNodeId ? (chunksFetched[activeNodeId] ?? 0) : 0
  const selectedHasContinuation = selectedNodeId
    ? continuations[selectedNodeId] != null
    : false

  // Initial graph load
  useEffect(() => {
    if (!entityId) return
    setIsLoading(true)
    setError(null)
    setChunksFetched({})
    setContinuations({})
    setExpandedNodeIds(new Set([entityId]))
    fetchGraphTraversal(entityId, entityType, expandDepth)
      .then((nh) => {
        setNeighborhood(nh)
        const continuationId = nh.continuation_id
        if (continuationId) {
          setContinuations((prev) => ({
            ...prev,
            [entityId]: continuationId,
          }))
        }
      })
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false))
  }, [entityId, entityType])

  // Expand: fetch neighborhood around selected node, merge into current
  async function handleExpand(nodeId: string, type: string) {
    setExpandingNodeId(nodeId)
    try {
      const newNh = await fetchGraphTraversal(nodeId, type, expandDepth)
      setNeighborhood((prev) => (prev ? mergeNeighborhood(prev, newNh) : newNh))
      const continuationId = newNh.continuation_id
      if (continuationId) {
        setContinuations((prev) => ({
          ...prev,
          [nodeId]: continuationId,
        }))
      }
      setExpandedNodeIds((prev) => new Set(prev).add(nodeId))
    } catch {
      // Expansion errors are non-critical — silently ignore
    } finally {
      setExpandingNodeId(null)
    }
  }

  // Fetch the next continuation chunk for the active node and merge it in.
  const loadMoreChunk = useCallback(async () => {
    if (!activeContinuation || loadingMore || !neighborhood) return
    const { nodeId, token } = activeContinuation
    const type =
      nodeId === entityId
        ? entityType
        : (neighborhood.nodes.find((n) => n.id === nodeId)?.type ?? entityType)
    setLoadingMore(true)
    try {
      const next = await fetchGraphTraversal(nodeId, type, expandDepth, token)
      setNeighborhood((prev) => (prev ? mergeNeighborhood(prev, next) : next))
      setContinuations((prev) => {
        const copy = { ...prev }
        if (next.continuation_id) copy[nodeId] = next.continuation_id
        else delete copy[nodeId]
        return copy
      })
      setChunksFetched((c) => ({ ...c, [nodeId]: (c[nodeId] ?? 0) + 1 }))
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)))
    } finally {
      setLoadingMore(false)
    }
  }, [
    activeContinuation,
    loadingMore,
    neighborhood,
    entityId,
    entityType,
    expandDepth,
  ])

  // Auto-continue: fetch up to AUTO_BATCH_LIMIT chunks automatically.
  useEffect(() => {
    if (!activeContinuation || loadingMore || autoFetched >= AUTO_BATCH_LIMIT)
      return
    // Defer to a macrotask so the fetch is scheduled after this commit rather
    // than firing setState synchronously inside the effect.
    const timer = setTimeout(loadMoreChunk, 0)
    return () => clearTimeout(timer)
  }, [activeContinuation, autoFetched, loadingMore, loadMoreChunk])

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
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "mt-2"
                  )}
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
            loadingMore={loadingMore}
            hasContinuation={selectedHasContinuation}
            onLoadMore={loadMoreChunk}
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
            {[1, 2].map((d) => (
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
