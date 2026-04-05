from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class MissingFieldReason(StrEnum):
    NOT_PROVIDED = "not_provided"
    EMPTY_VALUE = "empty_value"


class PaperRole(StrEnum):
    SEED = "seed"
    CANDIDATE = "candidate"


class CitationDirection(StrEnum):
    FORWARD = "forward"
    REVERSE = "reverse"


class SeedSourceKind(StrEnum):
    DIRECT_INPUT = "direct_input"
    SEARCH_DERIVED = "search_derived"


@dataclass(slots=True, frozen=True)
class AuthorSummary:
    name: str
    author_id: str | None = None


@dataclass(slots=True, frozen=True)
class PaperMetadata:
    provider: str
    role: PaperRole
    provider_paper_id: str | None
    title: str | None
    abstract: str | None
    authors: list[AuthorSummary]
    venue: str | None
    year: int | None
    citation_count: int | None
    external_ids: dict[str, str]
    provider_url: str | None
    open_access_pdf_url: str | None
    fields_of_study: list[str]
    tldr: str | None
    missing_fields: dict[str, MissingFieldReason] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["role"] = self.role.value
        payload["missing_fields"] = {
            name: reason.value for name, reason in self.missing_fields.items()
        }
        return payload


@dataclass(slots=True, frozen=True)
class CitationEdge:
    provider: str
    direction: CitationDirection
    source_paper_id: str
    target_paper_id: str
    seed_paper_id: str
    source_provenance: str
    contexts: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    is_influential: bool | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["direction"] = self.direction.value
        return payload


@dataclass(slots=True, frozen=True)
class DiscoveryWarning:
    code: str
    message: str
    provider: str
    direction: CitationDirection | None = None
    seed_identifier: str | None = None
    seed_paper_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.direction is not None:
            payload["direction"] = self.direction.value
        return payload


@dataclass(slots=True, frozen=True)
class DiscoverySeedProvenance:
    source_kind: SeedSourceKind
    input_identifier: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind.value,
            "input_identifier": self.input_identifier,
        }


@dataclass(slots=True, frozen=True)
class DiscoveryCandidateProvenance:
    seed_paper_id: str
    source_paper_id: str
    target_paper_id: str
    direction: CitationDirection
    source_provenance: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["direction"] = self.direction.value
        return payload


@dataclass(slots=True, frozen=True)
class DiscoverySeedArtifact:
    paper: PaperMetadata
    provenance: DiscoverySeedProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "paper": self.paper.to_dict(),
            "provenance": self.provenance.to_dict(),
        }


@dataclass(slots=True, frozen=True)
class DiscoveryCandidateArtifact:
    paper: PaperMetadata
    provenance: list[DiscoveryCandidateProvenance]
    score: "CandidateScore | None" = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "paper": self.paper.to_dict(),
            "provenance": [entry.to_dict() for entry in self.provenance],
        }
        if self.score is not None:
            payload["score"] = self.score.to_dict()
        return payload


@dataclass(slots=True, frozen=True)
class CitationExpansion:
    papers: list[PaperMetadata]
    edges: list[CitationEdge]
    warnings: list[DiscoveryWarning] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "papers": [paper.to_dict() for paper in self.papers],
            "edges": [edge.to_dict() for edge in self.edges],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


@dataclass(slots=True, frozen=True)
class DiscoveryCriteria:
    include_terms: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)
    preferred_terms: list[str] = field(default_factory=list)
    preferred_authors: list[str] = field(default_factory=list)
    preferred_venues: list[str] = field(default_factory=list)
    preferred_fields_of_study: list[str] = field(default_factory=list)
    min_year: int | None = None
    max_year: int | None = None
    min_citation_count: int | None = None
    text_weight: float = 1.0
    citation_weight: float = 0.35
    recency_weight: float = 0.25

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class CandidateScore:
    total: float
    components: dict[str, float]
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "components": dict(self.components),
            "reasons": list(self.reasons),
        }


@dataclass(slots=True, frozen=True)
class RankedCandidate:
    paper: PaperMetadata
    score: CandidateScore

    def to_dict(self) -> dict[str, object]:
        return {
            "paper": self.paper.to_dict(),
            "score": self.score.to_dict(),
        }


@dataclass(slots=True, frozen=True)
class DiscoveryRequest:
    identifiers: list[str]
    forward_limit: int
    reverse_limit: int
    criteria_source: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.criteria_source is None:
            payload.pop("criteria_source")
        return payload


@dataclass(slots=True, frozen=True)
class DiscoveryRunMetadata:
    provider: str
    generated_at: str
    request: DiscoveryRequest
    seed_count: int
    candidate_count: int
    edge_count: int
    warning_count: int
    partial_failure: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["request"] = self.request.to_dict()
        return payload


@dataclass(slots=True, frozen=True)
class DiscoveryRun:
    run_metadata: DiscoveryRunMetadata
    seeds: list[DiscoverySeedArtifact]
    candidates: list[DiscoveryCandidateArtifact]
    edges: list[CitationEdge]
    warnings: list[DiscoveryWarning] = field(default_factory=list)
    criteria: DiscoveryCriteria | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "run_metadata": self.run_metadata.to_dict(),
            "seeds": [seed.to_dict() for seed in self.seeds],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "edges": [edge.to_dict() for edge in self.edges],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }
        if self.criteria is not None:
            payload["criteria"] = self.criteria.to_dict()
        return payload
