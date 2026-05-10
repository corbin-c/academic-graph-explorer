"""
HAL SPARQL queries.

HAL (Hyper Articles en Ligne) is the French open archive for
scholarly publications.
"""

from app.sources.client import HttpSparqlClient

HAL_ENDPOINT = "https://data.archives-ouvertes.fr/sparql"


class HalSparqlClient(HttpSparqlClient):
    """SPARQL client for the HAL endpoint."""

    def __init__(self):
        super().__init__(HAL_ENDPOINT)
