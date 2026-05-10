"""
IdRef SPARQL queries.

IdRef (Identifiants et Référentiels) is the French national authority
file for higher education and research, maintained by ABES.
"""

from app.sources.client import HttpSparqlClient

IDREF_ENDPOINT = "https://data.idref.fr/sparql"


class IdRefSparqlClient(HttpSparqlClient):
    """SPARQL client for the IdRef endpoint."""

    def __init__(self):
        super().__init__(IDREF_ENDPOINT)
