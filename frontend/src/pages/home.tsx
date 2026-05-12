import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { searchApi, type SearchResult } from "@/lib/api"
import { SearchForm } from "@/components/search-form"
import { SearchResults } from "@/components/search-results"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

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
        <CardHeader className="text-center pb-6">
          <CardTitle className="text-3xl font-heading tracking-tight">
            Academic Graph Explorer
          </CardTitle>
          <CardDescription className="text-base">
            Explore connections between researchers and organizations
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-6">
          <SearchForm onSearch={handleSearch} isLoading={isLoading} />
          <SearchResults results={data} isLoading={isLoading} error={error} />
        </CardContent>
      </Card>
    </div>
  )
}
