import { useMemo } from "react"
import { User, Building2, BookOpen } from "lucide-react"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import type { GraphEntity, GraphEdge } from "@/lib/api"

interface LinkedNodesListProps {
  selectedNodeId: string
  nodes: GraphEntity[]
  edges: GraphEdge[]
  onSelectNode: (nodeId: string) => void
}

const typeIcons: Record<string, React.ReactNode> = {
  person: <User className="h-3.5 w-3.5" />,
  organization: <Building2 className="h-3.5 w-3.5" />,
  publication: <BookOpen className="h-3.5 w-3.5" />,
}

export function LinkedNodesList({
  selectedNodeId,
  nodes,
  edges,
  onSelectNode,
}: LinkedNodesListProps) {
  const { grouped, edgeTypesByTarget } = useMemo(() => {
    const linkedIds = new Set<string>()
    for (const edge of edges) {
      if (edge.source === selectedNodeId) linkedIds.add(edge.target)
      if (edge.target === selectedNodeId) linkedIds.add(edge.source)
    }

    const linked = nodes.filter((n) => n.id !== selectedNodeId && linkedIds.has(n.id))

    const groups: Record<string, GraphEntity[]> = {}
    for (const node of linked) {
      if (!groups[node.type]) groups[node.type] = []
      groups[node.type].push(node)
    }

    // Build edge type info for each linked node
    const edgeTypesByTarget = new Map<string, string[]>()
    for (const edge of edges) {
      const linkedId = edge.source === selectedNodeId ? edge.target
        : edge.target === selectedNodeId ? edge.source
        : null
      if (linkedId && edge.type) {
        if (!edgeTypesByTarget.has(linkedId)) edgeTypesByTarget.set(linkedId, [])
        edgeTypesByTarget.get(linkedId)!.push(edge.type)
      }
    }

    return { grouped: groups, edgeTypesByTarget }
  }, [selectedNodeId, nodes, edges])

  const entries = Object.entries(grouped)
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No linked entities found.</p>
    )
  }

  return (
    <div className="space-y-1">
      {entries.map(([type, items]) => (
        <Collapsible key={type}>
          <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium hover:bg-accent">
            {typeIcons[type] ?? <BookOpen className="h-3.5 w-3.5" />}
            <span className="capitalize">{type}s</span>
            <Badge variant="secondary" className="ml-auto text-xs">
              {items.length}
            </Badge>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul>
              {items.map((node) => (
                <li key={node.id}>
                  <button
                    onClick={() => onSelectNode(node.id)}
                    className="flex w-full items-center gap-2 truncate rounded-md px-2 py-1 pl-7 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
                  >
                    {node.label}
                  </button>
                  {edgeTypesByTarget.get(node.id)?.map((relType, j) => (
                    <div key={j} className="pl-7 text-xs text-muted-foreground/60">
                      {relType}
                    </div>
                  ))}
                </li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      ))}
    </div>
  )
}
