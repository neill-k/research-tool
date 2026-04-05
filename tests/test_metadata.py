from frontier_research.discovery.models import MissingFieldReason, PaperRole
from frontier_research.discovery.providers import normalize_semantic_scholar_paper


def test_normalization_keeps_same_shape_for_seed_and_candidate() -> None:
    payload = {
        "paperId": "abc123",
        "title": "A Paper",
        "abstract": "Useful abstract.",
        "authors": [{"name": "Ada Lovelace", "authorId": "1"}],
        "venue": "ICML",
        "year": 2024,
        "citationCount": 9,
        "externalIds": {"DOI": "10.1000/test"},
        "url": "https://example.com/paper",
        "openAccessPdf": {"url": "https://example.com/paper.pdf"},
        "fieldsOfStudy": ["Computer Science"],
        "tldr": {"text": "Short summary."},
    }

    seed = normalize_semantic_scholar_paper(payload, role=PaperRole.SEED).to_dict()
    candidate = normalize_semantic_scholar_paper(
        payload, role=PaperRole.CANDIDATE
    ).to_dict()

    assert set(seed.keys()) == set(candidate.keys())
    assert seed["role"] == "seed"
    assert candidate["role"] == "candidate"
    assert seed["missing_fields"] == {}
    assert candidate["missing_fields"] == {}


def test_normalization_marks_missing_fields_explicitly() -> None:
    payload = {
        "paperId": "abc123",
        "title": "  ",
        "abstract": None,
        "authors": [],
        "venue": None,
        "year": None,
        "citationCount": None,
        "externalIds": None,
        "url": None,
        "openAccessPdf": None,
        "fieldsOfStudy": [],
        "tldr": {"text": "   "},
    }

    metadata = normalize_semantic_scholar_paper(payload, role=PaperRole.SEED)

    assert metadata.title is None
    assert metadata.abstract is None
    assert metadata.authors == []
    assert metadata.missing_fields == {
        "title": MissingFieldReason.EMPTY_VALUE,
        "abstract": MissingFieldReason.NOT_PROVIDED,
        "authors": MissingFieldReason.EMPTY_VALUE,
        "venue": MissingFieldReason.NOT_PROVIDED,
        "year": MissingFieldReason.NOT_PROVIDED,
        "citationCount": MissingFieldReason.NOT_PROVIDED,
        "external_ids": MissingFieldReason.NOT_PROVIDED,
        "provider_url": MissingFieldReason.NOT_PROVIDED,
        "open_access_pdf_url": MissingFieldReason.NOT_PROVIDED,
        "fields_of_study": MissingFieldReason.EMPTY_VALUE,
        "tldr": MissingFieldReason.EMPTY_VALUE,
    }


def test_normalization_discards_invalid_author_entries() -> None:
    payload = {
        "paperId": "abc123",
        "title": "A Paper",
        "abstract": "Useful abstract.",
        "authors": [{"name": ""}, {"name": "Grace Hopper"}, "bad-entry"],
        "venue": "NeurIPS",
        "year": 2023,
        "citationCount": 5,
        "externalIds": {},
        "url": "https://example.com/paper",
        "openAccessPdf": {"url": "https://example.com/paper.pdf"},
        "fieldsOfStudy": ["Computer Science"],
        "tldr": None,
    }

    metadata = normalize_semantic_scholar_paper(payload, role=PaperRole.CANDIDATE)

    assert [author.name for author in metadata.authors] == ["Grace Hopper"]
    assert metadata.missing_fields["tldr"] == MissingFieldReason.NOT_PROVIDED
