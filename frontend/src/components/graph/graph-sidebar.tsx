import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { X, GitBranch, ChevronRight, Loader2, Check, Info } from "lucide-react"
import type { Neighborhood, GraphEntity, EntityDetail } from "@/lib/api"
import { fetchEntityDetail } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { IdentifierLinks } from "@/components/graph/identifier-links"
import { LinkedNodesList } from "@/components/graph/linked-nodes-list"

interface GraphSidebarProps {
  neighborhood: Neighborhood | undefined
  selectedNode: GraphEntity | undefined
  onSelectNode: (nodeId: string | null) => void
  onClose: () => void
}

function DetailContent({ detail }: { detail: EntityDetail }) {
  return (
    <div className="mt-2 space-y-1 text-xs text-muted-foreground">
      {detail.note && <p>{detail.note}</p>}
      {"organizations" in detail && detail.organizations.length > 0 && (
        <p>
          Organizations: {detail.organizations.map((o) => o.name).join(", ")}
        </p>
      )}
    </div>
  )
}

export function GraphSidebar({
  neighborhood,
  selectedNode,
  onSelectNode,
  onClose,
}: GraphSidebarProps) {
  const [detailRequested, setDetailRequested] = useState(false)

  const detailQuery = useQuery<EntityDetail>({
    queryKey: ["detail", selectedNode?.id, selectedNode?.type],
    queryFn: () =>
      fetchEntityDetail(
        selectedNode!.id,
        selectedNode!.type as "person" | "organization"
      ),
    enabled: detailRequested && !!selectedNode,
  })

  if (!selectedNode || !neighborhood) return null

  const showDetailButton =
    selectedNode.type === "person" || selectedNode.type === "organization"

  return (
    <div className="flex h-full w-[340px] shrink-0 flex-col border-l border-border bg-card">
      {/* Header with close */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="truncate text-sm font-heading font-medium">
          {selectedNode.label}
        </h2>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4">
          {/* Type badge */}
          <div>
            <Badge variant="secondary" className="capitalize">
              {selectedNode.type}
            </Badge>
          </div>

          {/* Identifiers */}
          {selectedNode.identifiers.length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Identifiers
                </h3>
                <IdentifierLinks identifiers={selectedNode.identifiers} />
              </div>
            </>
          )}

          {/* Details button */}
          {showDetailButton && (
            <>
              <Separator />
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setDetailRequested(true)}
                disabled={detailQuery.isLoading || detailQuery.isSuccess}
              >
                {detailQuery.isLoading ? (
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                ) : detailQuery.isSuccess ? (
                  <Check className="mr-2 h-3.5 w-3.5" />
                ) : (
                  <Info className="mr-2 h-3.5 w-3.5" />
                )}
                Details
              </Button>
              {detailQuery.data && (
                <DetailContent detail={detailQuery.data} />
              )}
              {detailQuery.isError && (
                <p className="text-xs text-destructive">
                  {detailQuery.error.message}
                </p>
              )}
            </>
          )}

          {/* Expand Graph (future) */}
          <Separator />
          <Button variant="outline" disabled className="w-full">
            <GitBranch className="mr-2 h-4 w-4" />
            Expand Graph
            <ChevronRight className="ml-auto h-4 w-4" />
          </Button>

          {/* Linked Nodes */}
          <Separator />
          <div>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Linked Entities
            </h3>
            <LinkedNodesList
              selectedNodeId={selectedNode.id}
              nodes={neighborhood.nodes}
              edges={neighborhood.edges}
              onSelectNode={onSelectNode}
            />
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
