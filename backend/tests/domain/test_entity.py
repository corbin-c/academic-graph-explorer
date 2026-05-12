from app.domain.entity import (
    Entity,
    EntityType,
    Identifier,
    Organization,
    Person,
    Publication,
    dedup_identifiers,
)


class TestEntityType:
    def test_person_type(self):
        assert EntityType.PERSON == "person"

    def test_publication_type(self):
        assert EntityType.PUBLICATION == "publication"

    def test_organization_type(self):
        assert EntityType.ORGANIZATION == "organization"

    def test_from_string(self):
        assert EntityType("person") == EntityType.PERSON
        assert EntityType("publication") == EntityType.PUBLICATION
        assert EntityType("organization") == EntityType.ORGANIZATION


class TestIdentifier:
    def test_create_identifier(self):
        ident = Identifier(scheme="orcid", value="0000-0001-2345-6789")
        assert ident.scheme == "orcid"
        assert ident.value == "0000-0001-2345-6789"


class TestDedupIdentifiers:
    def test_no_duplicates(self):
        idents = [
            Identifier(scheme="doi", value="a"),
            Identifier(scheme="doi", value="b"),
        ]
        assert dedup_identifiers(idents) == idents

    def test_removes_duplicates(self):
        idents = [
            Identifier(scheme="doi", value="a"),
            Identifier(scheme="doi", value="a"),
            Identifier(scheme="doi", value="b"),
        ]
        result = dedup_identifiers(idents)
        assert len(result) == 2
        assert result[0].value == "a"
        assert result[1].value == "b"

    def test_empty_list(self):
        assert dedup_identifiers([]) == []


class TestEntityBase:
    def test_base_entity(self):
        entity = Entity(id="1", label="Test", type=EntityType.PERSON)
        assert entity.id == "1"
        assert entity.label == "Test"
        assert entity.type == EntityType.PERSON
        assert entity.identifiers == []

    def test_serialize(self):
        entity = Entity(id="1", label="Test", type=EntityType.PERSON)
        data = entity.model_dump()
        assert data["id"] == "1"
        assert data["label"] == "Test"
        assert data["type"] == "person"


class TestOrganization:
    def test_create_organization(self):
        org = Organization(id="org-1", label="CNRS", note="French research org")
        assert org.id == "org-1"
        assert org.label == "CNRS"
        assert org.type == EntityType.ORGANIZATION
        assert org.note == "French research org"

    def test_create_minimal(self):
        org = Organization(id="org-1", label="CNRS")
        assert org.note is None

    def test_serialize(self):
        org = Organization(id="org-1", label="CNRS")
        data = org.model_dump()
        assert data["type"] == "organization"


class TestPerson:
    def test_create_person(self):
        person = Person(id="p1", label="Alice", note="Researcher")
        assert person.id == "p1"
        assert person.label == "Alice"
        assert person.type == EntityType.PERSON
        assert person.note == "Researcher"
        assert person.organizations == []

    def test_with_organizations(self):
        org = Organization(id="org-1", label="CNRS")
        person = Person(id="p1", label="Alice", organizations=[org])
        assert len(person.organizations) == 1
        assert person.organizations[0].label == "CNRS"

    def test_serialize(self):
        person = Person(id="p1", label="Alice")
        data = person.model_dump()
        assert data["type"] == "person"


class TestPublication:
    def test_create_publication(self):
        pub = Publication(id="pub-1", label="A Paper", doi="10.1234/x")
        assert pub.id == "pub-1"
        assert pub.label == "A Paper"
        assert pub.type == EntityType.PUBLICATION
        assert pub.doi == "10.1234/x"
        assert pub.identifiers == []

    def test_create_from_dict(self):
        data = {"id": "pub-2", "label": "Another", "doi": "10.1234/y"}
        pub = Publication.model_validate(data)
        assert pub.doi == "10.1234/y"

    def test_serialize(self):
        pub = Publication(id="pub-1", label="A Paper")
        data = pub.model_dump()
        assert data["type"] == "publication"
