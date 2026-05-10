from app.domain.entity import Entity, EntityType
from app.domain.graph import Neighborhood
from app.domain.relationship import Dataset, EntityId, Relationship, RelationshipType


class TestNeighborhood:
    def test_create_empty_neighborhood(self):
        center = Entity(id="c1", label="Center", type=EntityType.PERSON)
        nb = Neighborhood(center=center, nodes=[], edges=[])
        assert nb.center == center
        assert nb.nodes == []
        assert nb.edges == []

    def test_create_neighborhood_with_nodes_and_edges(self):
        center = Entity(id="c1", label="Center", type=EntityType.PERSON)
        node_a = Entity(id="a1", label="Co-author A", type=EntityType.PERSON)
        node_b = Entity(id="b1", label="Paper X", type=EntityType.PUBLICATION)

        edge = Relationship(
            source=EntityId(center.id),
            target=EntityId(node_a.id),
            type=RelationshipType.AUTHOR_OF,
            source_dataset=Dataset(name="IdRef"),
        )

        nb = Neighborhood(center=center, nodes=[node_a, node_b], edges=[edge])

        assert len(nb.nodes) == 2
        assert len(nb.edges) == 1
        assert nb.nodes[0].label == "Co-author A"
        assert nb.edges[0].type == RelationshipType.AUTHOR_OF

    def test_serialize_to_json(self):
        center = Entity(id="c1", label="Center", type=EntityType.PERSON)
        nb = Neighborhood(center=center, nodes=[], edges=[])
        data = nb.model_dump()
        assert data["center"]["id"] == "c1"
        assert data["nodes"] == []
        assert data["edges"] == []
