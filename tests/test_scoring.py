from __future__ import annotations

import pytest

from frontier_research.discovery.models import (
    AuthorSummary,
    CitationDirection,
    CitationEdge,
    PaperMetadata,
    PaperRole,
)
from frontier_research.discovery.service import (
    CriteriaValidationError,
    DiscoveryService,
    parse_criteria,
)
from tests.test_expansion import FakeProvider, build_paper


def build_candidate(
    paper_id: str,
    *,
    title: str,
    abstract: str,
    authors: list[str],
    venue: str,
    year: int,
    citation_count: int,
    fields_of_study: list[str],
) -> PaperMetadata:
    return PaperMetadata(
        provider="semantic_scholar",
        role=PaperRole.CANDIDATE,
        provider_paper_id=paper_id,
        title=title,
        abstract=abstract,
        authors=[AuthorSummary(name=name) for name in authors],
        venue=venue,
        year=year,
        citation_count=citation_count,
        external_ids={},
        provider_url=f"https://example.com/{paper_id}",
        open_access_pdf_url=None,
        fields_of_study=fields_of_study,
        tldr=None,
        missing_fields={},
    )


def build_edge(
    *,
    direction: CitationDirection,
    seed_paper_id: str,
    candidate_paper_id: str,
) -> CitationEdge:
    if direction is CitationDirection.FORWARD:
        source_paper_id = seed_paper_id
        target_paper_id = candidate_paper_id
    else:
        source_paper_id = candidate_paper_id
        target_paper_id = seed_paper_id
    return CitationEdge(
        provider="semantic_scholar",
        direction=direction,
        source_paper_id=source_paper_id,
        target_paper_id=target_paper_id,
        seed_paper_id=seed_paper_id,
        source_provenance="seed_citation_expansion",
        contexts=[],
        intents=[],
        is_influential=False,
    )


def test_parse_criteria_rejects_invalid_shapes_and_ranges() -> None:
    with pytest.raises(CriteriaValidationError) as exc_info:
        parse_criteria(
            {
                "include_terms": "ranking",
                "min_year": 2026,
                "max_year": 2025,
                "unknown_field": True,
            }
        )

    message = str(exc_info.value)
    assert "'include_terms' must be a list of strings." in message
    assert "'min_year' must be <= 'max_year'." in message
    assert "Unknown criteria field(s): unknown_field." in message


def test_rank_candidates_filters_scores_and_explains_ranking() -> None:
    seed = build_paper("seed-a", role=PaperRole.SEED, title="Neural retrieval ranking")
    candidate_top = build_candidate(
        "cand-top",
        title="Neural ranking systems",
        abstract="Improves neural retrieval for ranking tasks.",
        authors=["Grace Hopper"],
        venue="NeurIPS",
        year=2025,
        citation_count=25,
        fields_of_study=["Computer Science", "Machine Learning"],
    )
    candidate_author = build_candidate(
        "cand-author",
        title="Retrieval planning",
        abstract="Retrieval techniques from Ada Lovelace.",
        authors=["Ada Lovelace"],
        venue="ICML",
        year=2024,
        citation_count=12,
        fields_of_study=["Computer Science"],
    )
    candidate_filtered = build_candidate(
        "cand-filtered",
        title="Symbolic systems",
        abstract="Symbolic modeling without retrieval signals.",
        authors=["Claude Shannon"],
        venue="AAAI",
        year=2024,
        citation_count=30,
        fields_of_study=["Computer Science"],
    )

    criteria = parse_criteria(
        {
            "include_terms": ["retrieval"],
            "exclude_terms": ["symbolic"],
            "preferred_terms": ["ranking"],
            "preferred_authors": ["Ada Lovelace"],
            "preferred_venues": ["NeurIPS"],
            "min_year": 2024,
            "min_citation_count": 10,
        }
    )

    service = DiscoveryService(provider=FakeProvider(seeds={"seed-a": seed}))
    ranked, warnings = service.rank_candidates(
        seeds=[seed],
        candidates=[candidate_top, candidate_author],
        edges=[
            build_edge(
                direction=CitationDirection.FORWARD,
                seed_paper_id="seed-a",
                candidate_paper_id="cand-top",
            ),
            build_edge(
                direction=CitationDirection.REVERSE,
                seed_paper_id="seed-a",
                candidate_paper_id="cand-top",
            ),
            build_edge(
                direction=CitationDirection.FORWARD,
                seed_paper_id="seed-a",
                candidate_paper_id="cand-author",
            ),
        ],
        criteria=criteria,
    )

    assert [candidate.paper.provider_paper_id for candidate in ranked] == [
        "cand-top",
        "cand-author",
    ]
    assert ranked[0].score.total > ranked[1].score.total
    assert any(
        "preferred venue: NeurIPS" in reason for reason in ranked[0].score.reasons
    )
    assert any(
        "seed-context term" in reason for reason in ranked[0].score.reasons
    )
    assert warnings == []

    filtered_ranked, filtered_warnings = service.rank_candidates(
        seeds=[seed],
        candidates=[candidate_filtered],
        edges=[],
        criteria=criteria,
    )

    assert filtered_ranked == []
    assert [warning.code for warning in filtered_warnings] == [
        "criteria_filtered_candidate"
    ]
    assert "matched excluded term(s): symbolic" in filtered_warnings[0].message
