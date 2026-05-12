import { ExternalLink } from "lucide-react"
import type { Identifier } from "@/lib/api"

interface IdentifierLinksProps {
  identifiers: Identifier[]
}

function resolve(ident: Identifier): { label: string; url: string } | null {
  const v = ident.value

  // Raw DOI: "10.xxx/..."
  if (/^10\.\d{4,}/.test(v)) {
    return { label: "DOI", url: `https://doi.org/${v}` }
  }
  // DOI URL
  if (v.includes("doi.org")) {
    return { label: "DOI", url: v }
  }
  // BNF ARK
  if (v.includes("bnf.fr")) {
    return { label: "BNF", url: v }
  }
  if (v.startsWith("ark:/")) {
    return { label: "BNF", url: `https://catalogue.bnf.fr/${v}` }
  }
  // IdRef
  if (v.includes("idref.fr")) {
    return { label: "IdRef", url: v }
  }
  // VIAF
  if (v.includes("viaf.org")) {
    return { label: "VIAF", url: v }
  }
  // ORCID
  if (v.includes("orcid.org")) {
    return { label: "ORCID", url: v }
  }
  // Fallback — only if the value looks like a URL
  if (/^https?:\/\//.test(v)) {
    return { label: ident.scheme, url: v }
  }
  return null
}

export function IdentifierLinks({ identifiers }: IdentifierLinksProps) {
  if (identifiers.length === 0) return null

  return (
    <ul className="space-y-1">
      {identifiers.map((ident, i) => {
        const resolved = resolve(ident)
        if (!resolved) return null
        return (
          <li key={`${ident.scheme}-${i}`}>
            <a
              href={resolved.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-3 w-3 shrink-0" />
              {resolved.label}
            </a>
          </li>
        )
      })}
    </ul>
  )
}
