from app.domain.entity import Identifier, Publication


class TestPublication:
    def test_create_with_required_fields(self):
        pub = Publication(id="pub-1", title="A Groundbreaking Study")
        assert pub.id == "pub-1"
        assert pub.title == "A Groundbreaking Study"
        assert pub.doi is None
        assert pub.identifiers == []

    def test_create_with_all_fields(self):
        pub = Publication(
            id="pub-2",
            title="Another Paper",
            doi="10.1234/example",
            identifiers=[
                Identifier(scheme="owl:sameAs", value="https://doi.org/10.1234/example")
            ],
        )
        assert pub.doi == "10.1234/example"
        assert len(pub.identifiers) == 1
        assert pub.identifiers[0].scheme == "owl:sameAs"

    def test_create_from_dict(self):
        data = {
            "id": "pub-3",
            "title": "From Dict",
            "doi": "10.5678/dict",
            "identifiers": [{"scheme": "bibo:uri", "value": "https://example.com/doc"}],
        }
        pub = Publication.model_validate(data)
        assert pub.doi == "10.5678/dict"
        assert len(pub.identifiers) == 1
        assert pub.identifiers[0].scheme == "bibo:uri"
