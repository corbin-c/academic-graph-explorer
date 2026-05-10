from app.domain.publication import Publication


class TestPublication:
    def test_create_with_required_fields(self):
        pub = Publication(id="pub-1", title="A Groundbreaking Study")
        assert pub.id == "pub-1"
        assert pub.title == "A Groundbreaking Study"
        assert pub.doi is None
        assert pub.year is None

    def test_create_with_all_fields(self):
        pub = Publication(
            id="pub-2",
            title="Another Paper",
            doi="10.1234/example",
            year=2023,
        )
        assert pub.doi == "10.1234/example"
        assert pub.year == 2023

    def test_create_from_dict(self):
        data = {"id": "pub-3", "title": "From Dict", "year": 2020}
        pub = Publication.model_validate(data)
        assert pub.year == 2020
        assert pub.doi is None
