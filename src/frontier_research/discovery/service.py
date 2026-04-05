from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import log1p
import re

from frontier_research.discovery.models import (
    CandidateScore,
    CitationDirection,
    CitationExpansion,
    DiscoveryCandidateArtifact,
    DiscoveryCandidateProvenance,
    CitationEdge,
    DiscoveryCriteria,
    DiscoveryRequest,
    DiscoveryRun,
    DiscoveryRunMetadata,
    DiscoverySeedArtifact,
    DiscoverySeedProvenance,
    SeedSourceKind,
    DiscoveryWarning,
    PaperMetadata,
    PaperRole,
    RankedCandidate,
)
from frontier_research.discovery.providers import PaperMetadataProvider, ProviderRequestError

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(slots=True, frozen=True)
class CriteriaValidationError(ValueError):
    errors: list[str]

    def __str__(self) -> str:
        return "; ".join(self.errors)


@dataclass(slots=True)
class DiscoveryService:
    provider: PaperMetadataProvider

    def fetch(self, identifier: str, role: PaperRole) -> PaperMetadata:
        return self.provider.fetch_minimal_paper(identifier=identifier, role=role)

    def expand(
        self,
        identifiers: list[str],
        *,
        forward_limit: int,
        reverse_limit: int,
        criteria: DiscoveryCriteria | None = None,
        criteria_source: str | None = None,
    ) -> DiscoveryRun:
        seed_identifier_by_key: dict[str, str] = {}
        seeds_by_key: dict[str, PaperMetadata] = {}
        candidates_by_key: dict[str, PaperMetadata] = {}
        edges_by_key: dict[tuple[str, str, str, str, str], CitationEdge] = {}
        warnings: list[DiscoveryWarning] = []

        for identifier in identifiers:
            try:
                seed = self.fetch(identifier=identifier, role=PaperRole.SEED)
            except ProviderRequestError as exc:
                warnings.append(
                    self._warning_for_error(
                        exc,
                        code="seed_fetch_failed",
                        identifier=identifier,
                    )
                )
                continue

            seed_key = self._paper_key(seed)
            seeds_by_key[seed_key] = seed
            seed_identifier_by_key.setdefault(seed_key, identifier)

            directions: list[tuple[CitationDirection, int]] = []
            if forward_limit > 0:
                directions.append((CitationDirection.FORWARD, forward_limit))
            if reverse_limit > 0:
                directions.append((CitationDirection.REVERSE, reverse_limit))

            for direction, limit in directions:
                try:
                    expansion = self._expand_direction(
                        identifier=identifier,
                        seed=seed,
                        direction=direction,
                        limit=limit,
                    )
                except ProviderRequestError as exc:
                    warnings.append(
                        self._warning_for_error(
                            exc,
                            code="citation_expansion_failed",
                            identifier=identifier,
                            seed_paper_id=seed.provider_paper_id,
                            direction=direction,
                        )
                    )
                    continue

                warnings.extend(expansion.warnings)
                for paper in expansion.papers:
                    paper_key = self._paper_key(paper)
                    if paper_key == seed_key:
                        continue
                    candidates_by_key.setdefault(paper_key, paper)
                for edge in expansion.edges:
                    edge_key = (
                        edge.provider,
                        edge.direction.value,
                        edge.seed_paper_id,
                        edge.source_paper_id,
                        edge.target_paper_id,
                    )
                    edges_by_key.setdefault(edge_key, edge)

        candidates = list(candidates_by_key.values())
        edges = list(edges_by_key.values())
        ranked_candidates: list[RankedCandidate] = []
        if criteria is not None and candidates:
            ranked_candidates, criteria_warnings = self.rank_candidates(
                seeds=list(seeds_by_key.values()),
                candidates=candidates,
                edges=edges,
                criteria=criteria,
            )
            warnings.extend(criteria_warnings)
            candidates = [candidate.paper for candidate in ranked_candidates]
            retained_ids = {
                c.provider_paper_id for c in candidates if c.provider_paper_id
            }
            edges = [
                edge for edge in edges
                if edge.target_paper_id in retained_ids
                or edge.source_paper_id in retained_ids
                or edge.seed_paper_id in {s.provider_paper_id for s in seeds_by_key.values()}
            ]

        candidate_scores = {
            candidate.paper.provider_paper_id or self._paper_key(candidate.paper): candidate.score
            for candidate in ranked_candidates
        }
        candidate_provenance_by_id = self._candidate_provenance(edges)

        seed_artifacts = [
            DiscoverySeedArtifact(
                paper=seed,
                provenance=DiscoverySeedProvenance(
                    source_kind=SeedSourceKind.DIRECT_INPUT,
                    input_identifier=seed_identifier_by_key[self._paper_key(seed)],
                ),
            )
            for seed in seeds_by_key.values()
        ]
        candidate_artifacts = [
            DiscoveryCandidateArtifact(
                paper=candidate,
                provenance=candidate_provenance_by_id.get(
                    candidate.provider_paper_id or "",
                    [],
                ),
                score=candidate_scores.get(
                    candidate.provider_paper_id or self._paper_key(candidate)
                ),
            )
            for candidate in candidates
        ]

        metadata = DiscoveryRunMetadata(
            provider=self.provider.provider_name,
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request=DiscoveryRequest(
                identifiers=list(identifiers),
                forward_limit=forward_limit,
                reverse_limit=reverse_limit,
                criteria_source=criteria_source,
            ),
            seed_count=len(seed_artifacts),
            candidate_count=len(candidate_artifacts),
            edge_count=len(edges),
            warning_count=len(warnings),
            partial_failure=any(
                w.code in (
                    "seed_fetch_failed",
                    "citation_expansion_failed",
                    "provider_throttled",
                    "provider_partial_result",
                )
                for w in warnings
            ),
        )

        return DiscoveryRun(
            run_metadata=metadata,
            seeds=seed_artifacts,
            candidates=candidate_artifacts,
            edges=edges,
            warnings=warnings,
            criteria=criteria,
        )

    def rank_candidates(
        self,
        *,
        seeds: list[PaperMetadata],
        candidates: list[PaperMetadata],
        edges: list[CitationEdge],
        criteria: DiscoveryCriteria,
    ) -> tuple[list[RankedCandidate], list[DiscoveryWarning]]:
        edge_count_by_candidate: dict[str, int] = {}
        for edge in edges:
            if edge.direction is CitationDirection.FORWARD:
                candidate_id = edge.target_paper_id
            else:
                candidate_id = edge.source_paper_id
            edge_count_by_candidate[candidate_id] = (
                edge_count_by_candidate.get(candidate_id, 0) + 1
            )

        seed_terms = self._seed_terms(seeds)
        current_year = max((seed.year or 0) for seed in seeds) or date.today().year

        ranked: list[RankedCandidate] = []
        warnings: list[DiscoveryWarning] = []
        for candidate in candidates:
            rejection_reason = self._candidate_filter_rejection(
                candidate=candidate,
                criteria=criteria,
            )
            if rejection_reason is not None:
                warnings.append(
                    DiscoveryWarning(
                        code="criteria_filtered_candidate",
                        message=self._rejection(candidate, rejection_reason),
                        provider=candidate.provider,
                        seed_paper_id=None,
                    )
                )
                continue
            ranked.append(
                RankedCandidate(
                    paper=candidate,
                    score=self._score_candidate(
                        candidate=candidate,
                        criteria=criteria,
                        seed_terms=seed_terms,
                        citation_edges=edge_count_by_candidate.get(
                            candidate.provider_paper_id or "",
                            0,
                        ),
                        current_year=current_year,
                    ),
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score.total,
                item.paper.year is None,
                -(item.paper.year or 0),
                item.paper.title or "",
            )
        )
        return ranked, warnings

    def _expand_direction(
        self,
        *,
        identifier: str,
        seed: PaperMetadata,
        direction: CitationDirection,
        limit: int,
    ) -> CitationExpansion:
        seed_identifier = seed.provider_paper_id or identifier
        if direction is CitationDirection.FORWARD:
            return self.provider.expand_references(
                identifier=seed_identifier,
                seed_paper_id=seed_identifier,
                limit=limit,
            )
        return self.provider.expand_citations(
            identifier=seed_identifier,
            seed_paper_id=seed_identifier,
            limit=limit,
        )

    def _paper_key(self, paper: PaperMetadata) -> str:
        if paper.provider_paper_id:
            return f"{paper.provider}:{paper.provider_paper_id}"
        if doi := paper.external_ids.get("DOI"):
            return f"{paper.provider}:doi:{doi.lower()}"
        if corpus_id := paper.external_ids.get("CorpusId"):
            return f"{paper.provider}:corpus:{corpus_id}"
        if paper.provider_url:
            return f"{paper.provider}:url:{paper.provider_url}"
        title = (paper.title or "").strip().lower()
        year = paper.year if paper.year is not None else "unknown"
        return f"{paper.provider}:title:{title}:{year}"

    def _warning_for_error(
        self,
        exc: ProviderRequestError,
        *,
        code: str,
        identifier: str,
        seed_paper_id: str | None = None,
        direction: CitationDirection | None = None,
    ) -> DiscoveryWarning:
        warning_code = "provider_throttled" if exc.throttled else code
        return DiscoveryWarning(
            code=warning_code,
            message=str(exc),
            provider=exc.provider,
            direction=direction,
            seed_identifier=identifier,
            seed_paper_id=seed_paper_id,
        )

    def _candidate_provenance(
        self, edges: list[CitationEdge]
    ) -> dict[str, list[DiscoveryCandidateProvenance]]:
        provenance_by_candidate: dict[str, dict[tuple[str, str, str, str, str], DiscoveryCandidateProvenance]] = {}
        for edge in edges:
            candidate_id = (
                edge.target_paper_id
                if edge.direction is CitationDirection.FORWARD
                else edge.source_paper_id
            )
            provenance = DiscoveryCandidateProvenance(
                seed_paper_id=edge.seed_paper_id,
                source_paper_id=edge.source_paper_id,
                target_paper_id=edge.target_paper_id,
                direction=edge.direction,
                source_provenance=edge.source_provenance,
            )
            edge_key = (
                provenance.seed_paper_id,
                provenance.source_paper_id,
                provenance.target_paper_id,
                provenance.direction.value,
                provenance.source_provenance,
            )
            provenance_by_candidate.setdefault(candidate_id, {})[edge_key] = provenance

        return {
            candidate_id: list(entries.values())
            for candidate_id, entries in provenance_by_candidate.items()
        }

    def _seed_terms(self, seeds: list[PaperMetadata]) -> set[str]:
        tokens: set[str] = set()
        for seed in seeds:
            text_parts = [
                seed.title or "",
                seed.abstract or "",
                " ".join(seed.fields_of_study),
                seed.tldr or "",
                " ".join(author.name for author in seed.authors),
            ]
            for part in text_parts:
                tokens.update(self._tokenize(part))
        return tokens

    def _candidate_filter_rejection(
        self,
        *,
        candidate: PaperMetadata,
        criteria: DiscoveryCriteria,
    ) -> str | None:
        text_blob = self._candidate_text_blob(candidate)

        if criteria.min_year is not None and (
            candidate.year is None or candidate.year < criteria.min_year
        ):
            return f"year must be >= {criteria.min_year}"
        if criteria.max_year is not None and (
            candidate.year is None or candidate.year > criteria.max_year
        ):
            return f"year must be <= {criteria.max_year}"
        if criteria.min_citation_count is not None and (
            candidate.citation_count is None
            or candidate.citation_count < criteria.min_citation_count
        ):
            return f"citation_count must be >= {criteria.min_citation_count}"

        missing_include_terms = [
            term for term in criteria.include_terms if term.casefold() not in text_blob
        ]
        if missing_include_terms:
            return "missing required include term(s): " + ", ".join(
                sorted(missing_include_terms)
            )

        matched_excluded_terms = [
            term for term in criteria.exclude_terms if term.casefold() in text_blob
        ]
        if matched_excluded_terms:
            return "matched excluded term(s): " + ", ".join(
                sorted(matched_excluded_terms)
            )
        return None

    def _score_candidate(
        self,
        *,
        candidate: PaperMetadata,
        criteria: DiscoveryCriteria,
        seed_terms: set[str],
        citation_edges: int,
        current_year: int,
    ) -> CandidateScore:
        candidate_text_blob = self._candidate_text_blob(candidate)
        candidate_terms = self._candidate_terms(candidate)
        preferred_term_matches = sorted(
            term for term in criteria.preferred_terms if term.casefold() in candidate_text_blob
        )
        preferred_author_matches = sorted(
            author
            for author in criteria.preferred_authors
            if any(author.casefold() == paper_author.name.casefold() for paper_author in candidate.authors)
        )
        preferred_field_matches = sorted(
            field
            for field in criteria.preferred_fields_of_study
            if any(field.casefold() == fos.casefold() for fos in candidate.fields_of_study)
        )
        venue_match = (
            candidate.venue
            if candidate.venue
            and any(
                venue.casefold() == candidate.venue.casefold()
                for venue in criteria.preferred_venues
            )
            else None
        )

        seed_overlap = len(seed_terms.intersection(candidate_terms))
        explicit_overlap = sum(
            1 for term in criteria.include_terms + criteria.preferred_terms
            if term.casefold() in candidate_text_blob
        )
        text_component = (
            criteria.text_weight
            * (seed_overlap + (explicit_overlap * 2) + len(preferred_author_matches) + len(preferred_field_matches) + (1 if venue_match else 0))
        )
        citation_component = criteria.citation_weight * log1p(citation_edges)
        recency_component = 0.0
        if candidate.year is not None:
            age = max(current_year - candidate.year, 0)
            recency_component = criteria.recency_weight * max(0.0, 1 - (age / 10))

        components = {
            "text": round(text_component, 4),
            "citation_proximity": round(citation_component, 4),
            "recency": round(recency_component, 4),
        }
        total = round(sum(components.values()), 4)

        reasons: list[str] = []
        if seed_overlap:
            reasons.append(f"matched {seed_overlap} seed-context term(s)")
        if preferred_term_matches:
            reasons.append(
                "matched preferred term(s): " + ", ".join(preferred_term_matches)
            )
        if preferred_author_matches:
            reasons.append(
                "matched preferred author(s): " + ", ".join(preferred_author_matches)
            )
        if preferred_field_matches:
            reasons.append(
                "matched preferred field(s): " + ", ".join(preferred_field_matches)
            )
        if venue_match:
            reasons.append(f"published in preferred venue: {venue_match}")
        if citation_edges:
            reasons.append(f"linked to the seed set by {citation_edges} citation edge(s)")
        if candidate.year is not None:
            reasons.append(f"publication year {candidate.year} contributed to recency")

        return CandidateScore(total=total, components=components, reasons=reasons)

    def _candidate_terms(self, candidate: PaperMetadata) -> set[str]:
        terms: set[str] = set()
        text_parts = [
            candidate.title or "",
            candidate.abstract or "",
            candidate.venue or "",
            " ".join(candidate.fields_of_study),
            candidate.tldr or "",
            " ".join(author.name for author in candidate.authors),
        ]
        for part in text_parts:
            terms.update(self._tokenize(part))
        return terms

    def _candidate_text_blob(self, candidate: PaperMetadata) -> str:
        parts = [
            candidate.title or "",
            candidate.abstract or "",
            candidate.venue or "",
            " ".join(candidate.fields_of_study),
            candidate.tldr or "",
            " ".join(author.name for author in candidate.authors),
        ]
        return " ".join(parts).casefold()

    def _tokenize(self, text: str) -> set[str]:
        return {match.group(0) for match in TOKEN_PATTERN.finditer(text.casefold())}

    def _rejection(self, candidate: PaperMetadata, reason: str) -> str:
        identifier = candidate.provider_paper_id or candidate.title or "<unknown candidate>"
        return f"Candidate '{identifier}' failed discovery criteria: {reason}."


def parse_criteria(payload: object) -> DiscoveryCriteria:
    if not isinstance(payload, dict):
        raise CriteriaValidationError(
            ["Criteria payload must be a JSON object with named fields."]
        )

    errors: list[str] = []

    def parse_string_list(field_name: str) -> list[str]:
        raw_value = payload.get(field_name, [])
        if raw_value is None:
            return []
        if not isinstance(raw_value, list):
            errors.append(f"'{field_name}' must be a list of strings.")
            return []
        values: list[str] = []
        for item in raw_value:
            if not isinstance(item, str) or not item.strip():
                errors.append(
                    f"'{field_name}' entries must be non-empty strings."
                )
                continue
            values.append(item.strip())
        return values

    def parse_optional_int(field_name: str) -> int | None:
        raw_value = payload.get(field_name)
        if raw_value is None:
            return None
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            errors.append(f"'{field_name}' must be an integer.")
            return None
        return raw_value

    def parse_weight(field_name: str, default: float) -> float:
        raw_value = payload.get(field_name, default)
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            errors.append(f"'{field_name}' must be a number.")
            return default
        if raw_value < 0:
            errors.append(f"'{field_name}' must be >= 0.")
            return default
        return float(raw_value)

    criteria = DiscoveryCriteria(
        include_terms=parse_string_list("include_terms"),
        exclude_terms=parse_string_list("exclude_terms"),
        preferred_terms=parse_string_list("preferred_terms"),
        preferred_authors=parse_string_list("preferred_authors"),
        preferred_venues=parse_string_list("preferred_venues"),
        preferred_fields_of_study=parse_string_list("preferred_fields_of_study"),
        min_year=parse_optional_int("min_year"),
        max_year=parse_optional_int("max_year"),
        min_citation_count=parse_optional_int("min_citation_count"),
        text_weight=parse_weight("text_weight", 1.0),
        citation_weight=parse_weight("citation_weight", 0.35),
        recency_weight=parse_weight("recency_weight", 0.25),
    )

    if (
        criteria.min_year is not None
        and criteria.max_year is not None
        and criteria.min_year > criteria.max_year
    ):
        errors.append("'min_year' must be <= 'max_year'.")

    unknown_fields = sorted(set(payload.keys()) - set(criteria.to_dict().keys()))
    if unknown_fields:
        errors.append(
            "Unknown criteria field(s): " + ", ".join(unknown_fields) + "."
        )

    if errors:
        raise CriteriaValidationError(errors)
    return criteria
