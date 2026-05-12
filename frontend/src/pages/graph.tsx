import { useState, useMemo } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
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

  const {
    data: neighborhood,
    isLoading,
    error,
  } = useQuery<Neighborhood>({
    queryKey: ["graph", entityId!, entityType],
    queryFn: () => fetchGraphTraversal(entityId!, entityType),
    enabled: !!entityId,
  })

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
        {selectedNode && (
          <GraphSidebar
            neighborhood={neighborhood}
            selectedNode={selectedNode}
            onSelectNode={handleSelectNode}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>
    </div>
  )
}
