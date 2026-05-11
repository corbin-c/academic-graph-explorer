"""IdRef SOLR search client — queries the SRU/SOLR endpoint."""

import unicodedata
import urllib.parse

import httpx

SOLR_URL = "https://www.idref.fr/Sru/Solr"

_FIXED_PARAMS = {
    "sort": "esr_s asc",
    "version": "2.2",
    "start": "0",
    "rows": "30",
    "indent": "on",
    "fl": "id,ppn_z,recordtype_z,affcourt_z",
    "wt": "json",
}


def _sanitize_query(query: str) -> str:
    """Strip accents and lowercase for SOLR search."""
    normalized = unicodedata.normalize("NFKD", query)
    ascii_only = normalized.encode("ASCII", "ignore")
    return ascii_only.decode().lower()


class IdRefSearchClient:
    """Client for the IdRef SOLR search endpoint."""

    async def search(self, query: str) -> list[dict]:
        """Execute a SOLR search and return the raw docs array."""
        sanitized = _sanitize_query(query)
        params = {**_FIXED_PARAMS, "q": f"all:{sanitized}"}
        url = f"{SOLR_URL}?{urllib.parse.urlencode(params)}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data["response"]["docs"]
