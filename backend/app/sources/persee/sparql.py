"""
Persée SPARQL queries.

Persée is a French digital library of academic journals in
the humanities and social sciences.
"""

from app.sources.client import HttpSparqlClient

PERSEE_ENDPOINT = "https://data.persee.fr/sparql"


class PerseeSparqlClient(HttpSparqlClient):
    """SPARQL client for the Persée endpoint."""

    def __init__(self):
        super().__init__(PERSEE_ENDPOINT)
