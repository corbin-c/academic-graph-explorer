import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  Info,
  Loader2,
  ArrowRight,
  Building2,
} from "lucide-react"
import {
  fetchEntityDetail,
  type EntityDetail,
  type SearchResult,
} from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button, buttonVariants } from "@/components/ui/button"

interface SearchResultCardProps {
  result: SearchResult
}

function DetailContent({ detail }: { detail: EntityDetail }) {
  const hasNote = "note" in detail && detail.note != null
  const orgs = "organizations" in detail ? detail.organizations : []
  const hasOrgs = orgs.length > 0

  if (!hasNote && !hasOrgs) {
    return (
      <div className="mt-2 text-xs text-muted-foreground">
        No details available.
      </div>
    )
  }

  return (
    <div className="mt-2 space-y-1 text-xs text-muted-foreground">
      {"note" in detail && detail.note && <p>{detail.note}</p>}
      {"organizations" in detail && detail.organizations.length > 0 && (
        <>
          <p className="mt-2">Organizations:</p>
          <ul>
            {detail.organizations.map((o) => (
              <li key={o.id} className="flex items-center gap-1">
                <Building2 className="h-3 w-3 shrink-0 text-muted-foreground" />
                {o.label}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

export function SearchResultCard({ result }: SearchResultCardProps) {
  const [detailRequested, setDetailRequested] = useState(false)

  const detailQuery = useQuery<EntityDetail>({
    queryKey: ["detail", result.id, result.type],
    queryFn: () => fetchEntityDetail(result.id, result.type),
    enabled: detailRequested,
  })

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {!detailQuery.isSuccess && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDetailRequested(true)}
            disabled={detailQuery.isLoading}
          >
            {detailQuery.isLoading ? (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            ) : (
              <Info className="mr-1 h-3 w-3" />
            )}
            Details
          </Button>
        )}

        <Link
          to={`/graph/${encodeURIComponent(result.id)}?type=${result.type}`}
          className={cn(
            buttonVariants({ variant: "outline", size: "lg" }),
            "ml-auto"
          )}
        >
          Explore Graph <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
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
