import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { searchApi, type SearchResult } from "@/lib/api"
import { SearchForm } from "@/components/search-form"
import { SearchResults } from "@/components/search-results"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"

export function HomePage() {
  const [query, setQuery] = useState("")

  const { data, isLoading, error } = useQuery<SearchResult[]>({
    queryKey: ["search", query],
    queryFn: () => searchApi(query),
    enabled: query.length > 0,
  })

  function handleSearch(q: string) {
    setQuery(q)
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center px-4">
      <Card className="w-full max-w-2xl border-none shadow-none">
        <CardHeader className="pt-2 text-center">
          <CardTitle className="mb-2 font-heading text-3xl tracking-tight">
            Academic Graph Explorer
          </CardTitle>
          <CardDescription className="text-base">
            Discover researchers, publications, and organizations through their
            connections
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6 p-8">
          <p>
            Academic research is represented across interconnected datasets:
            people, publications, institutions, theses, and the relationships
            between them.
          </p>
          <p>
            Search for a researcher or organization, then progressively explore
            its network of scholarly relationships.
          </p>
        </CardContent>
        <CardContent className="flex flex-col items-center gap-6">
          <SearchForm onSearch={handleSearch} isLoading={isLoading} />
          <SearchResults results={data} isLoading={isLoading} error={error} />
          <em className="mt-4 text-center text-xs text-muted-foreground">
            Currently powered by IdRef, SPARQL and French scholarly linked data.
            <br />
            <a
              href="https://www.github.com/corbin-c/academic-graph-explorer/"
              target="_blank"
              className="hover:underline"
            >
              Learn more
            </a>
          </em>
        </CardContent>
      </Card>
    </div>
  )
}
