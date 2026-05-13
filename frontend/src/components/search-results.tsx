import { User, Building2 } from "lucide-react"
import type { SearchResult } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { SearchResultCard } from "@/components/search-result-card"

interface SearchResultsProps {
  results: SearchResult[] | undefined
  isLoading: boolean
  error: Error | null
}

export function SearchResults({
  results,
  isLoading,
  error,
}: SearchResultsProps) {
  if (isLoading) {
    return <p className="text-center text-muted-foreground">Searching...</p>
  }

  if (error) {
    return (
      <p className="text-center text-destructive">Error: {error.message}</p>
    )
  }

  if (!results || results.length === 0) {
    return (
      <p>
        Try it:{" "}
        <a href="/graph/056802315?type=person&depth=2">Didier Veillon</a> |{" "}
        <a href="/graph/227816196?type=organization&depth=2">PRISM Lab</a> |{" "}
        <a href="/graph/139753753?type=person&depth=2">Marin Dacos</a>
      </p>
    )
  }

  return (
    <div className="w-full max-w-xl space-y-3">
      {results.map((result) => (
        <Card key={result.id}>
          <CardHeader className="pb-2">
            <CardTitle className="flex w-full items-center justify-between text-base">
              <div className="flex items-center gap-2">
                {result.type === "person" ? (
                  <User className="h-4 w-4 shrink-0 text-muted-foreground" />
                ) : (
                  <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
                {result.name}
              </div>
              <Badge
                variant={result.type === "person" ? "default" : "secondary"}
              >
                {result.type}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <SearchResultCard result={result} />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
