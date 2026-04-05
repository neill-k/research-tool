from __future__ import annotations

from dataclasses import dataclass

from frontier_research.discovery.models import (
    CitationDirection,
    CitationEdge,
    DiscoveryRun,
    DiscoveryWarning,
    PaperMetadata,
    PaperRole,
)
from frontier_research.discovery.providers import PaperMetadataProvider, ProviderRequestError


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
    ) -> DiscoveryRun:
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

        return DiscoveryRun(
            seeds=list(seeds_by_key.values()),
            candidates=list(candidates_by_key.values()),
            edges=list(edges_by_key.values()),
            warnings=warnings,
        )

    def _expand_direction(
        self,
        *,
        identifier: str,
        seed: PaperMetadata,
        direction: CitationDirection,
        limit: int,
    ):
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
