import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Info, GitBranch, Check, Loader2 } from "lucide-react"
import { fetchEntityDetail, fetchGraphTraversal, type EntityDetail, type SearchResult } from "@/lib/api"
import { Button } from "@/components/ui/button"

interface SearchResultCardProps {
  result: SearchResult
}

function DetailContent({ detail }: { detail: EntityDetail }) {
  return (
    <div className="mt-2 space-y-1">
      {detail.note && (
        <p className="text-sm text-muted-foreground">{detail.note}</p>
      )}
      {"organizations" in detail && detail.organizations.length > 0 && (
        <p className="text-sm">
          Organizations:{" "}
          {detail.organizations.map((o) => o.name).join(", ")}
        </p>
      )}
    </div>
  )
}

export function SearchResultCard({ result }: SearchResultCardProps) {
  const [detailRequested, setDetailRequested] = useState(false)
  const [graphRequested, setGraphRequested] = useState(false)

  const detailQuery = useQuery<EntityDetail>({
    queryKey: ["detail", result.id, result.type],
    queryFn: () => fetchEntityDetail(result.id, result.type),
    enabled: detailRequested,
  })

  const graphQuery = useQuery({
    queryKey: ["graph", result.id, result.type],
    queryFn: () => fetchGraphTraversal(result.id, result.type),
    enabled: graphRequested,
  })

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setDetailRequested(true)}
          disabled={detailQuery.isLoading || detailQuery.isSuccess}
        >
          {detailQuery.isLoading ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : detailQuery.isSuccess ? (
            <Check className="mr-1 h-3 w-3" />
          ) : (
            <Info className="mr-1 h-3 w-3" />
          )}
          Details
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setGraphRequested(true)}
          disabled={graphQuery.isLoading || graphQuery.isSuccess}
        >
          {graphQuery.isLoading ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : graphQuery.isSuccess ? (
            <Check className="mr-1 h-3 w-3" />
          ) : (
            <GitBranch className="mr-1 h-3 w-3" />
          )}
          Graph (depth=1)
        </Button>
      </div>

      {detailQuery.isError && (
        <p className="text-sm text-destructive">
          Error: {detailQuery.error.message}
        </p>
      )}

      {detailQuery.data && <DetailContent detail={detailQuery.data} />}
    </div>
  )
}
