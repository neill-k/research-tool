from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from frontier_research.discovery.models import (
    AuthorSummary,
    CitationDirection,
    CitationEdge,
    CitationExpansion,
    DiscoveryWarning,
    MissingFieldReason,
    PaperMetadata,
    PaperRole,
)


SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,abstract,authors,venue,year,citationCount,externalIds,url,"
    "openAccessPdf,fieldsOfStudy,tldr"
)
SEMANTIC_SCHOLAR_REFERENCE_FIELDS = (
    "contexts,intents,isInfluential,citedPaper.paperId,citedPaper.title,"
    "citedPaper.abstract,citedPaper.authors,citedPaper.venue,citedPaper.year,"
    "citedPaper.citationCount,citedPaper.externalIds,citedPaper.url,"
    "citedPaper.openAccessPdf,citedPaper.fieldsOfStudy"
)
SEMANTIC_SCHOLAR_CITATION_FIELDS = (
    "contexts,intents,isInfluential,citingPaper.paperId,citingPaper.title,"
    "citingPaper.abstract,citingPaper.authors,citingPaper.venue,citingPaper.year,"
    "citingPaper.citationCount,citingPaper.externalIds,citingPaper.url,"
    "citingPaper.openAccessPdf,citingPaper.fieldsOfStudy"
)


class PaperMetadataProvider(Protocol):
    provider_name: str

    def fetch_minimal_paper(self, identifier: str, role: PaperRole) -> PaperMetadata:
        """Fetch a normalized paper metadata record."""

    def expand_references(self, identifier: str, seed_paper_id: str, limit: int) -> CitationExpansion:
        """Fetch references for a resolved seed paper."""

    def expand_citations(self, identifier: str, seed_paper_id: str, limit: int) -> CitationExpansion:
        """Fetch citations for a resolved seed paper."""


@dataclass(slots=True, frozen=True)
class ProviderRequestError(Exception):
    message: str
    provider: str
    status_code: int | None = None
    throttled: bool = False

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class SemanticScholarMetadataProvider:
    timeout_seconds: float = 15.0
    provider_name: str = "semantic_scholar"

    def fetch_minimal_paper(self, identifier: str, role: PaperRole) -> PaperMetadata:
        encoded_identifier = quote(identifier, safe="")
        payload = self._get_json(
            f"/graph/v1/paper/{encoded_identifier}?fields={SEMANTIC_SCHOLAR_FIELDS}",
            identifier=identifier,
        )
        return normalize_semantic_scholar_paper(payload, role=role)

    def expand_references(
        self, identifier: str, seed_paper_id: str, limit: int
    ) -> CitationExpansion:
        return self._expand_direction(
            identifier=identifier,
            seed_paper_id=seed_paper_id,
            direction=CitationDirection.FORWARD,
            limit=limit,
            path_suffix="references",
            fields=SEMANTIC_SCHOLAR_REFERENCE_FIELDS,
            nested_paper_key="citedPaper",
        )

    def expand_citations(
        self, identifier: str, seed_paper_id: str, limit: int
    ) -> CitationExpansion:
        return self._expand_direction(
            identifier=identifier,
            seed_paper_id=seed_paper_id,
            direction=CitationDirection.REVERSE,
            limit=limit,
            path_suffix="citations",
            fields=SEMANTIC_SCHOLAR_CITATION_FIELDS,
            nested_paper_key="citingPaper",
        )

    def _expand_direction(
        self,
        *,
        identifier: str,
        seed_paper_id: str,
        direction: CitationDirection,
        limit: int,
        path_suffix: str,
        fields: str,
        nested_paper_key: str,
    ) -> CitationExpansion:
        if limit <= 0:
            return CitationExpansion(papers=[], edges=[], warnings=[])

        encoded_identifier = quote(identifier, safe="")
        collected_papers: list[PaperMetadata] = []
        collected_edges: list[CitationEdge] = []
        warnings: list[DiscoveryWarning] = []
        offset = 0

        while len(collected_papers) < limit:
            remaining = limit - len(collected_papers)
            payload = self._get_json(
                (
                    f"/graph/v1/paper/{encoded_identifier}/{path_suffix}"
                    f"?fields={fields}&offset={offset}&limit={min(remaining, 1000)}"
                ),
                identifier=identifier,
            )
            entries = payload.get("data")
            if entries is None:
                warnings.append(
                    DiscoveryWarning(
                        code="provider_partial_result",
                        message=(
                            f"Semantic Scholar returned no '{path_suffix}' list for seed "
                            f"'{identifier}'."
                        ),
                        provider=self.provider_name,
                        direction=direction,
                        seed_identifier=identifier,
                        seed_paper_id=seed_paper_id,
                    )
                )
                break
            if not isinstance(entries, list):
                raise ProviderRequestError(
                    message=(
                        f"Semantic Scholar returned an unexpected '{path_suffix}' payload for "
                        f"'{identifier}'."
                    ),
                    provider=self.provider_name,
                )
            if not entries:
                break

            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                nested_paper = entry.get(nested_paper_key)
                if not isinstance(nested_paper, dict):
                    continue
                paper = normalize_semantic_scholar_paper(
                    nested_paper,
                    role=PaperRole.CANDIDATE,
                )
                edge = normalize_semantic_scholar_edge(
                    entry,
                    direction=direction,
                    seed_paper_id=seed_paper_id,
                    candidate_paper_id=paper.provider_paper_id,
                    provider=self.provider_name,
                )
                if edge is None:
                    continue
                collected_papers.append(paper)
                collected_edges.append(edge)
                if len(collected_papers) >= limit:
                    break

            next_offset = payload.get("next")
            if not isinstance(next_offset, int) or next_offset <= offset:
                break
            offset = next_offset

        return CitationExpansion(
            papers=collected_papers,
            edges=collected_edges,
            warnings=warnings,
        )

    def _get_json(self, path: str, *, identifier: str) -> dict[str, Any]:
        url = f"https://api.semanticscholar.org{path}"
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except HTTPError as exc:
            raise ProviderRequestError(
                message=(
                    f"Semantic Scholar request failed with HTTP {exc.code} for "
                    f"'{identifier}'."
                ),
                provider=self.provider_name,
                status_code=exc.code,
                throttled=exc.code == 429,
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(
                message=(
                    f"Semantic Scholar request failed for '{identifier}': {exc.reason}."
                ),
                provider=self.provider_name,
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderRequestError(
                message=f"Semantic Scholar returned a non-object payload for '{identifier}'.",
                provider=self.provider_name,
            )
        return payload


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


def normalize_semantic_scholar_edge(
    payload: dict[str, Any],
    *,
    direction: CitationDirection,
    seed_paper_id: str,
    candidate_paper_id: str | None,
    provider: str,
) -> CitationEdge | None:
    if candidate_paper_id is None:
        return None

    contexts = [
        item.strip()
        for item in payload.get("contexts", [])
        if isinstance(item, str) and item.strip()
    ]
    intents = [
        item.strip()
        for item in payload.get("intents", [])
        if isinstance(item, str) and item.strip()
    ]
    is_influential = payload.get("isInfluential")
    if not isinstance(is_influential, bool):
        is_influential = None

    if direction is CitationDirection.FORWARD:
        source_paper_id = seed_paper_id
        target_paper_id = candidate_paper_id
    else:
        source_paper_id = candidate_paper_id
        target_paper_id = seed_paper_id

    return CitationEdge(
        provider=provider,
        direction=direction,
        source_paper_id=source_paper_id,
        target_paper_id=target_paper_id,
        seed_paper_id=seed_paper_id,
        source_provenance="seed_citation_expansion",
        contexts=contexts,
        intents=intents,
        is_influential=is_influential,
    )
