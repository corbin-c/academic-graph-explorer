"""
IdRef resource helpers.

IdRef provides REST endpoints for bibliographic data:
    References:  https://www.idref.fr/services/references/{ppn}.json
    Biblio:      https://www.idref.fr/services/biblio/{ppn}.json
"""

import httpx

IDREF_REFERENCES_URL = "https://www.idref.fr/services/references/{ppn}.json"
IDREF_BIBLIO_URL = "https://www.idref.fr/services/biblio/{ppn}.json"


class IdRefResourcesClient:
    """Client for IdRef bibliographic resource endpoints."""

    async def get_references(self, ppn: str) -> dict:
        """
        Fetch bibliographic references for an IdRef person.

        Args:
            ppn: IdRef PPN identifier (e.g. "121375307").

        Returns:
            JSON response with bibliographic references.
        """
        url = IDREF_REFERENCES_URL.format(ppn=ppn)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def get_biblio(self, ppn: str) -> dict:
        """
        Fetch full bibliography for an IdRef person.

        Args:
            ppn: IdRef PPN identifier (e.g. "121375307").

        Returns:
            JSON response with bibliographic records.
        """
        url = IDREF_BIBLIO_URL.format(ppn=ppn)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
