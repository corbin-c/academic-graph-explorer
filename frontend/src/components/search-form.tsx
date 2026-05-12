import { useState, type FormEvent } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface SearchFormProps {
  onSearch: (query: string) => void
  isLoading: boolean
}

export function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [query, setQuery] = useState("")

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    onSearch(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-xl gap-2">
      <Input
        type="text"
        placeholder="Search for researchers or organizations..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={isLoading}
        className="flex-1"
      />
      <Button type="submit" disabled={isLoading || !query.trim()}>
        <Search className="mr-2 h-4 w-4" />
        Search
      </Button>
    </form>
  )
}
