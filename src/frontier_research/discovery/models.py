from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class MissingFieldReason(StrEnum):
    NOT_PROVIDED = "not_provided"
    EMPTY_VALUE = "empty_value"


class PaperRole(StrEnum):
    SEED = "seed"
    CANDIDATE = "candidate"


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
