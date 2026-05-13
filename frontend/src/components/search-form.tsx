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
    <form
      onSubmit={handleSubmit}
      className="flex w-full max-w-xl items-end gap-2"
    >
      <label className="flex-1 text-muted-foreground">
        Search for a researcher or an organization
        <Input
          type="search"
          placeholder="Marin Dacos"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isLoading}
          className="mt-1 text-foreground"
        />
      </label>
      <Button type="submit" disabled={isLoading || !query.trim()}>
        <Search className="mr-2 h-4 w-4" />
        Search
      </Button>
    </form>
  )
}
