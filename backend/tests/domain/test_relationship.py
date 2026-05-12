from app.domain.relationship import Dataset, EntityId, Relationship


class TestEntityId:
    def test_entity_id_is_string(self):
        eid = EntityId("http://www.idref.fr/139753753/id")
        assert eid == "http://www.idref.fr/139753753/id"
        assert isinstance(eid, str)


class TestDataset:
    def test_create_minimal_dataset(self):
        ds = Dataset(name="IdRef")
        assert ds.name == "IdRef"
        assert ds.endpoint is None

    def test_create_with_endpoint(self):
        ds = Dataset(name="HAL", endpoint="https://sparql.archives-ouvertes.fr/sparql")
        assert ds.endpoint == "https://sparql.archives-ouvertes.fr/sparql"


class TestRelationship:
    def test_create_relationship(self):
        source = EntityId("http://www.idref.fr/001/id")
        target = EntityId("http://www.idref.fr/002/id")
        rel = Relationship(
            source=source,
            target=target,
            type="authorOf",
            source_dataset=Dataset(name="IdRef"),
        )
        assert rel.source == source
        assert rel.target == target
        assert rel.type == "authorOf"
        assert rel.source_dataset.name == "IdRef"

    def test_free_form_type_string(self):
        """Relationship type is free-form, not a closed enum."""
        rel = Relationship(
            source=EntityId("s"),
            target=EntityId("t"),
            type="directedBy",
            source_dataset=Dataset(name="IdRef"),
        )
        assert rel.type == "directedBy"

    def test_create_from_dict(self):
        data = {
            "source": "http://www.idref.fr/001/id",
            "target": "http://www.idref.fr/002/id",
            "type": "affiliatedWith",
            "source_dataset": {
                "name": "IdRef",
                "endpoint": "https://data.idref.fr/sparql",
            },
        }
        rel = Relationship.model_validate(data)
        assert rel.type == "affiliatedWith"
