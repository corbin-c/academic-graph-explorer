"""
SUDOC — French academic union catalogue.

SUDOC exposes individual document records as RDF/XML at:
    https://www.sudoc.fr/{PPN}.rdf

Fields available: dc:title, dc:date, dcterms:abstract, bibo:uri (full-text URL),
marcrel:aut (authors), and others.
"""

import httpx

SUDOC_RDF_TEMPLATE = "https://www.sudoc.fr/{ppn}.rdf"


class SudocClient:
    """Client for fetching SUDOC document records as RDF/XML."""

    async def fetch_rdf(self, ppn: str) -> str:
        """
        Fetch the RDF/XML record for a SUDOC document.

        Args:
            ppn: SUDOC PPN identifier (e.g. "121375307").

        Returns:
            RDF/XML content as a string.
        """
        url = SUDOC_RDF_TEMPLATE.format(ppn=ppn)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text
