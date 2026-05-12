import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  Info,
  GitBranch,
  Check,
  Loader2,
  BookOpen,
  Users,
  ArrowRight,
  Building2,
} from "lucide-react"
import {
  fetchEntityDetail,
  fetchPersonContributions,
  fetchOrganizationPublications,
  fetchOrganizationMembers,
  type EntityDetail,
  type Contribution,
  type PublicationRef,
  type PersonRef,
  type SearchResult,
} from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button, buttonVariants } from "@/components/ui/button"

interface SearchResultCardProps {
  result: SearchResult
}

function DetailContent({ detail }: { detail: EntityDetail }) {
  return (
    <div className="mt-2 space-y-1 text-xs text-muted-foreground">
      {detail.note && <p>{detail.note}</p>}
      {"organizations" in detail && detail.organizations.length > 0 && (
        <p className="mt-2">
          Organizations:
          <ul>
            {detail.organizations.map((o) => (
              <li key={o.id} className="flex items-center gap-1">
                <Building2 className="h-3 w-3 shrink-0 text-muted-foreground" />

                {o.name}
              </li>
            ))}
          </ul>
        </p>
      )}
    </div>
  )
}

export function SearchResultCard({ result }: SearchResultCardProps) {
  const [detailRequested, setDetailRequested] = useState(false)
  const [contributionsRequested, setContributionsRequested] = useState(false)
  const [publicationsRequested, setPublicationsRequested] = useState(false)
  const [membersRequested, setMembersRequested] = useState(false)

  const detailQuery = useQuery<EntityDetail>({
    queryKey: ["detail", result.id, result.type],
    queryFn: () => fetchEntityDetail(result.id, result.type),
    enabled: detailRequested,
  })

  const contributionsQuery = useQuery<Contribution[]>({
    queryKey: ["contributions", result.id],
    queryFn: () => fetchPersonContributions(result.id),
    enabled: contributionsRequested,
  })

  const publicationsQuery = useQuery<PublicationRef[]>({
    queryKey: ["publications", result.id],
    queryFn: () => fetchOrganizationPublications(result.id),
    enabled: publicationsRequested,
  })

  const membersQuery = useQuery<PersonRef[]>({
    queryKey: ["members", result.id],
    queryFn: () => fetchOrganizationMembers(result.id),
    enabled: membersRequested,
  })

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
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

        <Link
          to={`/graph/${encodeURIComponent(result.id)}?type=${result.type}`}
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "ml-auto")}
        >
          Explore Graph <ArrowRight className="ml-2 h-4 w-4" />
        </Link>

        {/* {result.type === "person" && ( */}
        {/*   <Button */}
        {/*     variant="outline" */}
        {/*     size="sm" */}
        {/*     onClick={() => setContributionsRequested(true)} */}
        {/*     disabled={contributionsQuery.isLoading || contributionsQuery.isSuccess} */}
        {/*   > */}
        {/*     {contributionsQuery.isLoading ? ( */}
        {/*       <Loader2 className="mr-1 h-3 w-3 animate-spin" /> */}
        {/*     ) : contributionsQuery.isSuccess ? ( */}
        {/*       <Check className="mr-1 h-3 w-3" /> */}
        {/*     ) : ( */}
        {/*       <BookOpen className="mr-1 h-3 w-3" /> */}
        {/*     )} */}
        {/*     Contributions */}
        {/*   </Button> */}
        {/* )} */}
        {/**/}
        {/* {result.type === "organization" && ( */}
        {/*   <> */}
        {/*     <Button */}
        {/*       variant="outline" */}
        {/*       size="sm" */}
        {/*       onClick={() => setPublicationsRequested(true)} */}
        {/*       disabled={publicationsQuery.isLoading || publicationsQuery.isSuccess} */}
        {/*     > */}
        {/*       {publicationsQuery.isLoading ? ( */}
        {/*         <Loader2 className="mr-1 h-3 w-3 animate-spin" /> */}
        {/*       ) : publicationsQuery.isSuccess ? ( */}
        {/*         <Check className="mr-1 h-3 w-3" /> */}
        {/*       ) : ( */}
        {/*         <BookOpen className="mr-1 h-3 w-3" /> */}
        {/*       )} */}
        {/*       Publications */}
        {/*     </Button> */}
        {/**/}
        {/*     <Button */}
        {/*       variant="outline" */}
        {/*       size="sm" */}
        {/*       onClick={() => setMembersRequested(true)} */}
        {/*       disabled={membersQuery.isLoading || membersQuery.isSuccess} */}
        {/*     > */}
        {/*       {membersQuery.isLoading ? ( */}
        {/*         <Loader2 className="mr-1 h-3 w-3 animate-spin" /> */}
        {/*       ) : membersQuery.isSuccess ? ( */}
        {/*         <Check className="mr-1 h-3 w-3" /> */}
        {/*       ) : ( */}
        {/*         <Users className="mr-1 h-3 w-3" /> */}
        {/*       )} */}
        {/*       Members */}
        {/*     </Button> */}
        {/*   </> */}
        {/* )} */}
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
