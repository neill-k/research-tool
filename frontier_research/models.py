from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Paper:
    paper_id: str
    title: str
    abstract: str
    year: int
    authors: list[str]
    keywords: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CitationEdge:
    source_paper_id: str
    target_paper_id: str
    direction: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ResolvedSeed:
    input_type: str
    input_value: str
    resolution_kind: str
    paper: Paper
    why_selected: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["paper"] = self.paper.to_dict()
        return payload


@dataclass(slots=True)
class RankedCandidate:
    paper: Paper
    score: float
    ranking_reasons: list[str]
    matched_terms: list[str]
    citation_links_to_seeds: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["paper"] = self.paper.to_dict()
        return payload


@dataclass(slots=True)
class DiscoveryRequest:
    paper_inputs: list[str]
    concept_inputs: list[str]
    question_inputs: list[str]
    forward_depth: int = 1
    reverse_depth: int = 1
    max_candidates: int = 10
    must_match: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    year_min: int | None = None


@dataclass(slots=True)
class DiscoveryResult:
    request: DiscoveryRequest
    resolved_seeds: list[ResolvedSeed]
    candidate_papers: list[RankedCandidate]
    citation_edges: list[CitationEdge]

    def to_dict(self) -> dict:
        return {
            "request": asdict(self.request),
            "resolved_seeds": [seed.to_dict() for seed in self.resolved_seeds],
            "candidate_papers": [candidate.to_dict() for candidate in self.candidate_papers],
            "citation_edges": [edge.to_dict() for edge in self.citation_edges],
        }
