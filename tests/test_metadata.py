import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from frontier_research.discovery.models import CitationDirection, MissingFieldReason, PaperRole
from frontier_research.discovery.providers import (
    ProviderRequestError,
    SemanticScholarMetadataProvider,
    normalize_semantic_scholar_edge,
    normalize_semantic_scholar_paper,
)


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
        "citation_count": MissingFieldReason.NOT_PROVIDED,
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
    assert metadata.missing_fields["external_ids"] == MissingFieldReason.EMPTY_VALUE


def test_edge_normalization_preserves_direction_and_context() -> None:
    payload = {
        "contexts": [" cited in passing ", None],
        "intents": ["background", ""],
        "isInfluential": True,
    }

    edge = normalize_semantic_scholar_edge(
        payload,
        direction=CitationDirection.REVERSE,
        seed_paper_id="seed-1",
        candidate_paper_id="cand-1",
        provider="semantic_scholar",
    )

    assert edge is not None
    assert edge.direction is CitationDirection.REVERSE
    assert edge.source_paper_id == "cand-1"
    assert edge.target_paper_id == "seed-1"
    assert edge.contexts == ["cited in passing"]
    assert edge.intents == ["background"]


SAMPLE_PAPER_PAYLOAD = {
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


def _mock_urlopen(payload: object):
    """Return a context manager that yields a file-like JSON response."""
    body = json.dumps(payload).encode()
    response = io.BytesIO(body)
    response.status = 200

    class _FakeResponse:
        def __enter__(self):
            return response

        def __exit__(self, *_):
            pass

    return _FakeResponse()


def test_fetch_minimal_paper_success(monkeypatch) -> None:
    provider = SemanticScholarMetadataProvider()
    monkeypatch.setattr(
        "frontier_research.discovery.providers.urlopen",
        lambda url, timeout=None: _mock_urlopen(SAMPLE_PAPER_PAYLOAD),
    )
    paper = provider.fetch_minimal_paper("abc123", role=PaperRole.SEED)
    assert paper.provider_paper_id == "abc123"
    assert paper.title == "A Paper"
    assert paper.role is PaperRole.SEED
    assert paper.missing_fields == {}


def test_fetch_minimal_paper_http_error(monkeypatch) -> None:
    provider = SemanticScholarMetadataProvider()

    def raise_404(url, timeout=None):
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(
        "frontier_research.discovery.providers.urlopen",
        raise_404,
    )
    with pytest.raises(ProviderRequestError) as exc_info:
        provider.fetch_minimal_paper("bad-id", role=PaperRole.SEED)
    assert exc_info.value.status_code == 404
    assert not exc_info.value.throttled


def test_fetch_minimal_paper_throttled(monkeypatch) -> None:
    provider = SemanticScholarMetadataProvider()

    def raise_429(url, timeout=None):
        raise HTTPError(url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(
        "frontier_research.discovery.providers.urlopen",
        raise_429,
    )
    with pytest.raises(ProviderRequestError) as exc_info:
        provider.fetch_minimal_paper("some-id", role=PaperRole.SEED)
    assert exc_info.value.status_code == 429
    assert exc_info.value.throttled
