import { User, Building2 } from "lucide-react"
import type { SearchResult } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface SearchResultsProps {
  results: SearchResult[] | undefined
  isLoading: boolean
  error: Error | null
}

export function SearchResults({ results, isLoading, error }: SearchResultsProps) {
  if (isLoading) {
    return (
      <p className="text-muted-foreground text-center">Searching...</p>
    )
  }

  if (error) {
    return (
      <p className="text-destructive text-center">
        Error: {error.message}
      </p>
    )
  }

  if (!results || results.length === 0) {
    return null
  }

  return (
    <div className="w-full max-w-xl space-y-3">
      {results.map((result) => (
        <Card key={result.id}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              {result.type === "person" ? (
                <User className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Building2 className="h-4 w-4 text-muted-foreground" />
              )}
              {result.name}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <Badge variant={result.type === "person" ? "default" : "secondary"}>
              {result.type}
            </Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
