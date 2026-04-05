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
class DiscoveryRun:
    seeds: list[PaperMetadata]
    candidates: list[PaperMetadata]
    edges: list[CitationEdge]
    warnings: list[DiscoveryWarning] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "seeds": [paper.to_dict() for paper in self.seeds],
            "candidates": [paper.to_dict() for paper in self.candidates],
            "edges": [edge.to_dict() for edge in self.edges],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }
