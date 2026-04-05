from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from frontier_research.discovery.models import (
    AuthorSummary,
    MissingFieldReason,
    PaperMetadata,
    PaperRole,
)


SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,abstract,authors,venue,year,citationCount,externalIds,url,"
    "openAccessPdf,fieldsOfStudy,tldr"
)


class PaperMetadataProvider(Protocol):
    provider_name: str

    def fetch_minimal_paper(self, identifier: str, role: PaperRole) -> PaperMetadata:
        """Fetch a normalized paper metadata record."""


@dataclass(slots=True)
class SemanticScholarMetadataProvider:
    timeout_seconds: float = 15.0
    provider_name: str = "semantic_scholar"

    def fetch_minimal_paper(self, identifier: str, role: PaperRole) -> PaperMetadata:
        encoded_identifier = quote(identifier, safe="")
        url = (
            "https://api.semanticscholar.org/graph/v1/paper/"
            f"{encoded_identifier}?fields={SEMANTIC_SCHOLAR_FIELDS}"
        )
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(
                f"Semantic Scholar request failed with HTTP {exc.code} for '{identifier}'."
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Semantic Scholar request failed for '{identifier}': {exc.reason}."
            ) from exc

        return normalize_semantic_scholar_paper(payload, role=role)


def normalize_semantic_scholar_paper(
    payload: dict[str, Any], *, role: PaperRole
) -> PaperMetadata:
    missing_fields: dict[str, MissingFieldReason] = {}

    def maybe_text(field_name: str) -> str | None:
        value = payload.get(field_name)
        if value is None:
            missing_fields[field_name] = MissingFieldReason.NOT_PROVIDED
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        missing_fields[field_name] = MissingFieldReason.EMPTY_VALUE
        return None

    def maybe_int(field_name: str) -> int | None:
        value = payload.get(field_name)
        if value is None:
            missing_fields[field_name] = MissingFieldReason.NOT_PROVIDED
            return None
        if isinstance(value, bool):
            missing_fields[field_name] = MissingFieldReason.EMPTY_VALUE
            return None
        if isinstance(value, int):
            return value
        missing_fields[field_name] = MissingFieldReason.EMPTY_VALUE
        return None

    authors_payload = payload.get("authors")
    authors: list[AuthorSummary] = []
    if isinstance(authors_payload, list):
        for author in authors_payload:
            if not isinstance(author, dict):
                continue
            name = author.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            author_id = author.get("authorId")
            authors.append(
                AuthorSummary(
                    name=name.strip(),
                    author_id=author_id if isinstance(author_id, str) else None,
                )
            )
    else:
        missing_fields["authors"] = MissingFieldReason.NOT_PROVIDED
    if isinstance(authors_payload, list) and not authors:
        missing_fields["authors"] = MissingFieldReason.EMPTY_VALUE

    external_ids_payload = payload.get("externalIds")
    external_ids: dict[str, str] = {}
    if isinstance(external_ids_payload, dict):
        for key, value in external_ids_payload.items():
            if isinstance(key, str) and isinstance(value, str) and value.strip():
                external_ids[key] = value.strip()
    elif external_ids_payload is None:
        missing_fields["external_ids"] = MissingFieldReason.NOT_PROVIDED
    else:
        missing_fields["external_ids"] = MissingFieldReason.EMPTY_VALUE

    fos_payload = payload.get("fieldsOfStudy")
    fields_of_study = [
        item.strip()
        for item in fos_payload
        if isinstance(item, str) and item.strip()
    ] if isinstance(fos_payload, list) else []
    if fos_payload is None:
        missing_fields["fields_of_study"] = MissingFieldReason.NOT_PROVIDED
    elif not fields_of_study:
        missing_fields["fields_of_study"] = MissingFieldReason.EMPTY_VALUE

    open_access_pdf_url = None
    open_access_payload = payload.get("openAccessPdf")
    if isinstance(open_access_payload, dict):
        candidate_url = open_access_payload.get("url")
        if isinstance(candidate_url, str) and candidate_url.strip():
            open_access_pdf_url = candidate_url.strip()
        else:
            missing_fields["open_access_pdf_url"] = MissingFieldReason.EMPTY_VALUE
    elif open_access_payload is None:
        missing_fields["open_access_pdf_url"] = MissingFieldReason.NOT_PROVIDED
    else:
        missing_fields["open_access_pdf_url"] = MissingFieldReason.EMPTY_VALUE

    tldr_payload = payload.get("tldr")
    tldr = None
    if isinstance(tldr_payload, dict):
        text = tldr_payload.get("text")
        if isinstance(text, str) and text.strip():
            tldr = text.strip()
        else:
            missing_fields["tldr"] = MissingFieldReason.EMPTY_VALUE
    elif tldr_payload is None:
        missing_fields["tldr"] = MissingFieldReason.NOT_PROVIDED
    else:
        missing_fields["tldr"] = MissingFieldReason.EMPTY_VALUE

    provider_paper_id = payload.get("paperId")
    if not isinstance(provider_paper_id, str) or not provider_paper_id.strip():
        missing_fields["provider_paper_id"] = (
            MissingFieldReason.NOT_PROVIDED
            if provider_paper_id is None
            else MissingFieldReason.EMPTY_VALUE
        )
        provider_paper_id = None
    else:
        provider_paper_id = provider_paper_id.strip()

    provider_url = maybe_text("url")
    if "url" in missing_fields:
        missing_fields["provider_url"] = missing_fields.pop("url")

    return PaperMetadata(
        provider="semantic_scholar",
        role=role,
        provider_paper_id=provider_paper_id,
        title=maybe_text("title"),
        abstract=maybe_text("abstract"),
        authors=authors,
        venue=maybe_text("venue"),
        year=maybe_int("year"),
        citation_count=maybe_int("citationCount"),
        external_ids=external_ids,
        provider_url=provider_url,
        open_access_pdf_url=open_access_pdf_url,
        fields_of_study=fields_of_study,
        tldr=tldr,
        missing_fields=missing_fields,
    )
