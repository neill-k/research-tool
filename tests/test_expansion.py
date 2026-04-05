from __future__ import annotations

from dataclasses import dataclass, field

from frontier_research.discovery.models import (
    CitationDirection,
    CitationEdge,
    CitationExpansion,
    DiscoveryWarning,
    PaperMetadata,
    PaperRole,
)
from frontier_research.discovery.providers import ProviderRequestError
from frontier_research.discovery.service import DiscoveryService


def build_paper(
    paper_id: str,
    *,
    role: PaperRole,
    title: str,
) -> PaperMetadata:
    return PaperMetadata(
        provider="semantic_scholar",
        role=role,
        provider_paper_id=paper_id,
        title=title,
        abstract=f"{title} abstract",
        authors=[],
        venue=None,
        year=2024,
        citation_count=1,
        external_ids={},
        provider_url=f"https://example.com/{paper_id}",
        open_access_pdf_url=None,
        fields_of_study=["Computer Science"],
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


@dataclass
class FakeProvider:
    provider_name: str = "semantic_scholar"
    seeds: dict[str, PaperMetadata] = field(default_factory=dict)
    references: dict[str, CitationExpansion] = field(default_factory=dict)
    citations: dict[str, CitationExpansion] = field(default_factory=dict)
    failures: dict[tuple[str, str], ProviderRequestError] = field(default_factory=dict)

    def fetch_minimal_paper(self, identifier: str, role: PaperRole) -> PaperMetadata:
        return self.seeds[identifier]

    def expand_references(self, identifier: str, seed_paper_id: str, limit: int) -> CitationExpansion:
        failure = self.failures.get(("references", identifier))
        if failure is not None:
            raise failure
        return self.references[identifier]

    def expand_citations(self, identifier: str, seed_paper_id: str, limit: int) -> CitationExpansion:
        failure = self.failures.get(("citations", identifier))
        if failure is not None:
            raise failure
        return self.citations[identifier]


def test_expand_deduplicates_candidates_and_edges_across_seed_neighborhoods() -> None:
    seed_a = build_paper("seed-a", role=PaperRole.SEED, title="Seed A")
    seed_b = build_paper("seed-b", role=PaperRole.SEED, title="Seed B")
    shared_candidate = build_paper("cand-1", role=PaperRole.CANDIDATE, title="Shared")

    provider = FakeProvider(
        seeds={"seed-a": seed_a, "seed-b": seed_b},
        references={
            "seed-a": CitationExpansion(
                papers=[shared_candidate],
                edges=[
                    build_edge(
                        direction=CitationDirection.FORWARD,
                        seed_paper_id="seed-a",
                        candidate_paper_id="cand-1",
                    )
                ],
            ),
            "seed-b": CitationExpansion(
                papers=[shared_candidate],
                edges=[
                    build_edge(
                        direction=CitationDirection.FORWARD,
                        seed_paper_id="seed-b",
                        candidate_paper_id="cand-1",
                    )
                ],
            ),
        },
        citations={
            "seed-a": CitationExpansion(papers=[], edges=[]),
            "seed-b": CitationExpansion(papers=[], edges=[]),
        },
    )

    run = DiscoveryService(provider=provider).expand(
        identifiers=["seed-a", "seed-b"],
        forward_limit=5,
        reverse_limit=0,
    )

    assert run.run_metadata.request.to_dict() == {
        "identifiers": ["seed-a", "seed-b"],
        "forward_limit": 5,
        "reverse_limit": 0,
    }
    assert [seed.paper.provider_paper_id for seed in run.seeds] == ["seed-a", "seed-b"]
    assert [candidate.paper.provider_paper_id for candidate in run.candidates] == ["cand-1"]
    assert {
        (entry.seed_paper_id, entry.direction.value)
        for entry in run.candidates[0].provenance
    } == {
        ("seed-a", "forward"),
        ("seed-b", "forward"),
    }
    assert {
        (edge.seed_paper_id, edge.source_paper_id, edge.target_paper_id)
        for edge in run.edges
    } == {
        ("seed-a", "seed-a", "cand-1"),
        ("seed-b", "seed-b", "cand-1"),
    }


def test_expand_keeps_partial_results_when_one_direction_fails() -> None:
    seed = build_paper("seed-a", role=PaperRole.SEED, title="Seed A")
    reverse_candidate = build_paper("cand-2", role=PaperRole.CANDIDATE, title="Reverse")

    provider = FakeProvider(
        seeds={"seed-a": seed},
        references={"seed-a": CitationExpansion(papers=[], edges=[])},
        citations={
            "seed-a": CitationExpansion(
                papers=[reverse_candidate],
                edges=[
                    build_edge(
                        direction=CitationDirection.REVERSE,
                        seed_paper_id="seed-a",
                        candidate_paper_id="cand-2",
                    )
                ],
                warnings=[
                    DiscoveryWarning(
                        code="provider_partial_result",
                        message="Reference list unavailable.",
                        provider="semantic_scholar",
                        direction=CitationDirection.REVERSE,
                        seed_identifier="seed-a",
                        seed_paper_id="seed-a",
                    )
                ],
            )
        },
        failures={
            (
                "references",
                "seed-a",
            ): ProviderRequestError(
                message="Semantic Scholar request failed with HTTP 429 for 'seed-a'.",
                provider="semantic_scholar",
                status_code=429,
                throttled=True,
            )
        },
    )

    run = DiscoveryService(provider=provider).expand(
        identifiers=["seed-a"],
        forward_limit=3,
        reverse_limit=3,
    )

    assert [candidate.paper.provider_paper_id for candidate in run.candidates] == ["cand-2"]
    assert [(edge.source_paper_id, edge.target_paper_id) for edge in run.edges] == [
        ("cand-2", "seed-a")
    ]
    assert [warning.code for warning in run.warnings] == [
        "provider_throttled",
        "provider_partial_result",
    ]
    assert run.run_metadata.partial_failure is True

