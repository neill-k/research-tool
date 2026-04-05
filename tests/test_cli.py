from __future__ import annotations

from frontier_research.discovery.cli import render_text_run
from frontier_research.discovery.models import (
    CandidateScore,
    CitationDirection,
    CitationEdge,
    DiscoveryCandidateArtifact,
    DiscoveryCandidateProvenance,
    DiscoveryRequest,
    DiscoveryRun,
    DiscoveryRunMetadata,
    DiscoverySeedArtifact,
    DiscoverySeedProvenance,
    PaperMetadata,
    PaperRole,
    SeedSourceKind,
)


def build_paper(paper_id: str, *, role: PaperRole, title: str) -> PaperMetadata:
    return PaperMetadata(
        provider="semantic_scholar",
        role=role,
        provider_paper_id=paper_id,
        title=title,
        abstract=f"{title} abstract",
        authors=[],
        venue="NeurIPS",
        year=2025,
        citation_count=3,
        external_ids={},
        provider_url=f"https://example.com/{paper_id}",
        open_access_pdf_url=None,
        fields_of_study=["Computer Science"],
        tldr=None,
        missing_fields={},
    )


def test_render_text_run_includes_metadata_provenance_and_scores() -> None:
    seed = build_paper("seed-a", role=PaperRole.SEED, title="Seed A")
    candidate = build_paper("cand-a", role=PaperRole.CANDIDATE, title="Candidate A")
    run = DiscoveryRun(
        run_metadata=DiscoveryRunMetadata(
            provider="semantic_scholar",
            generated_at="2026-04-05T09:15:00Z",
            request=DiscoveryRequest(
                identifiers=["seed-a"],
                forward_limit=5,
                reverse_limit=2,
                criteria_source="criteria.json",
            ),
            seed_count=1,
            candidate_count=1,
            edge_count=1,
            warning_count=0,
            partial_failure=False,
        ),
        seeds=[
            DiscoverySeedArtifact(
                paper=seed,
                provenance=DiscoverySeedProvenance(
                    source_kind=SeedSourceKind.DIRECT_INPUT,
                    input_identifier="seed-a",
                ),
            )
        ],
        candidates=[
            DiscoveryCandidateArtifact(
                paper=candidate,
                provenance=[
                    DiscoveryCandidateProvenance(
                        seed_paper_id="seed-a",
                        source_paper_id="seed-a",
                        target_paper_id="cand-a",
                        direction=CitationDirection.FORWARD,
                        source_provenance="seed_citation_expansion",
                    )
                ],
                score=CandidateScore(
                    total=2.5,
                    components={"text": 2.0, "citation_proximity": 0.5, "recency": 0.0},
                    reasons=["matched preferred term(s): ranking"],
                ),
            )
        ],
        edges=[
            CitationEdge(
                provider="semantic_scholar",
                direction=CitationDirection.FORWARD,
                source_paper_id="seed-a",
                target_paper_id="cand-a",
                seed_paper_id="seed-a",
                source_provenance="seed_citation_expansion",
            )
        ],
        warnings=[],
    )

    rendered = render_text_run(run)

    assert "Discovery Run" in rendered
    assert "Criteria Source: criteria.json" in rendered
    assert "Seed A [direct_input: seed-a]" in rendered
    assert "Candidate A (score=2.5000)" in rendered
    assert "via forward citation from seed seed-a" in rendered
