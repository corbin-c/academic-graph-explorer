"""Pre-loaded SPARQL query templates for IdRef."""

from pathlib import Path


_QUERIES_DIR = Path(__file__).resolve().parent


def load_sparql(filename: str) -> str:
    """Read a .sparql file from the queries directory."""
    return (_QUERIES_DIR / filename).read_text()


PERSON = load_sparql("person.sparql")
PERSON_CONTRIBUTIONS = load_sparql("person_contributions.sparql")
ORGANIZATION = load_sparql("organization.sparql")
ORGANIZATION_MEMBERS = load_sparql("organization_members.sparql")
ORGANIZATION_PUBLICATIONS = load_sparql("organization_publications.sparql")
PUBLICATION = load_sparql("publication.sparql")
PUBLICATION_PERSONS = load_sparql("publication_persons.sparql")
PUBLICATION_ORGANIZATIONS = load_sparql("publication_organizations.sparql")
