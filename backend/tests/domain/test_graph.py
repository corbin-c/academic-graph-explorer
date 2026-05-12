from app.domain.entity import Person, Publication
from app.domain.graph import Neighborhood
from app.domain.relationship import Dataset, EntityId, Relationship


class TestNeighborhood:
    def test_create_empty_neighborhood(self):
        center = Person(id="c1", label="Center")
        nb = Neighborhood(center=center, nodes=[], edges=[])
        assert nb.center == center
        assert nb.nodes == []
        assert nb.edges == []

    def test_create_neighborhood_with_nodes_and_edges(self):
        center = Person(id="c1", label="Center")
        node_a = Person(id="a1", label="Co-author A")
        node_b = Publication(id="b1", label="Paper X")

        edge = Relationship(
            source=EntityId(center.id),
            target=EntityId(node_a.id),
            type="authorOf",
            source_dataset=Dataset(name="IdRef"),
        )

        nb = Neighborhood(center=center, nodes=[node_a, node_b], edges=[edge])

        assert len(nb.nodes) == 2
        assert len(nb.edges) == 1
        assert nb.nodes[0].label == "Co-author A"
        assert nb.edges[0].type == "authorOf"

    def test_serialize_to_json(self):
        center = Person(id="c1", label="Center")
        nb = Neighborhood(center=center, nodes=[], edges=[])
        data = nb.model_dump()
        assert data["center"]["id"] == "c1"
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_subclass_serialization(self):
        """Person subclasses retain their fields in Neighborhood.nodes."""
        person = Person(
            id="p1",
            label="Alice",
            note="A note",
        )
        nb = Neighborhood(center=person, nodes=[person], edges=[])
        data = nb.model_dump()
        node = data["nodes"][0]
        assert node["type"] == "person"
        assert node["note"] == "A note"
