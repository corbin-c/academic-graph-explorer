"""
IdRef search — SOLR-based person lookup.

IdRef exposes a SOLR search API for raw person search:
    https://www.idref.fr/Sru/Solr?q=persname_t:(TERM1 AND TERM2)&wt=json&fl=*
"""

import httpx

IDREF_SOLR_URL = "https://www.idref.fr/Sru/Solr"


class IdRefSearchClient:
    """Client for searching IdRef persons via the SOLR API."""

    async def search_person(self, name: str) -> dict:
        """
        Search for a person by name.

        Args:
            name: Person name, e.g. "Marin Dacos".

        Returns:
            SOLR JSON response with matching person records.
        """
        terms = " AND ".join(name.split())
        params = {
            "q": f"persname_t:({terms})",
            "wt": "json",
            "fl": "*",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(IDREF_SOLR_URL, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
