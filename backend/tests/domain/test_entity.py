from app.domain.entity import Entity, EntityType, Identifier


class TestIdentifier:
    def test_create_identifier(self):
        ident = Identifier(scheme="orcid", value="0000-0001-2345-6789")
        assert ident.scheme == "orcid"
        assert ident.value == "0000-0001-2345-6789"

    def test_create_from_dict(self):
        ident = Identifier.model_validate({"scheme": "doi", "value": "10.1234/foo"})
        assert ident.scheme == "doi"
        assert ident.value == "10.1234/foo"


class TestEntityType:
    def test_person_type(self):
        assert EntityType.PERSON == "person"

    def test_publication_type(self):
        assert EntityType.PUBLICATION == "publication"

    def test_from_string(self):
        assert EntityType("organization") == EntityType.ORGANIZATION


class TestEntity:
    def test_create_minimal_entity(self):
        entity = Entity(id="123", label="John Doe", type=EntityType.PERSON)
        assert entity.id == "123"
        assert entity.label == "John Doe"
        assert entity.type == EntityType.PERSON
        assert entity.identifiers == []

    def test_create_with_identifiers(self):
        entity = Entity(
            id="456",
            label="Some Paper",
            type=EntityType.PUBLICATION,
            identifiers=[Identifier(scheme="doi", value="10.1234/bar")],
        )
        assert len(entity.identifiers) == 1
        assert entity.identifiers[0].scheme == "doi"

    def test_create_from_dict(self):
        data = {
            "id": "789",
            "label": "Test Lab",
            "type": "organization",
            "identifiers": [{"scheme": "ror", "value": "https://ror.org/01an7q238"}],
        }
        entity = Entity.model_validate(data)
        assert entity.id == "789"
        assert entity.type == EntityType.ORGANIZATION
        assert entity.identifiers[0].scheme == "ror"

    def test_entity_serializes_to_json(self):
        entity = Entity(id="abc", label="Test", type=EntityType.ORGANIZATION)
        json_data = entity.model_dump()
        assert json_data == {
            "id": "abc",
            "label": "Test",
            "type": "organization",
            "identifiers": [],
        }
