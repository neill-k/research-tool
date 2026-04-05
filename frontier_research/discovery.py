from __future__ import annotations

from collections import defaultdict

from frontier_research.models import CitationEdge, DiscoveryRequest, DiscoveryResult, RankedCandidate, ResolvedSeed
from frontier_research.providers import DiscoveryProvider, tokenize


def run_discovery(request: DiscoveryRequest, provider: DiscoveryProvider) -> DiscoveryResult:
    resolved_seeds = _resolve_seeds(request, provider)
    edges, candidate_ids = _expand_candidates(request, provider, resolved_seeds)
    ranked_candidates = _rank_candidates(request, provider, resolved_seeds, candidate_ids)
    return DiscoveryResult(
        request=request,
        resolved_seeds=resolved_seeds,
        candidate_papers=ranked_candidates,
        citation_edges=edges,
    )


def _resolve_seeds(request: DiscoveryRequest, provider: DiscoveryProvider) -> list[ResolvedSeed]:
    resolved: list[ResolvedSeed] = []

    for paper_input in request.paper_inputs:
        paper = provider.resolve_paper(paper_input)
        resolved.append(
            ResolvedSeed(
                input_type="paper",
                input_value=paper_input,
                resolution_kind="direct_paper_seed",
                paper=paper,
                why_selected="Resolved directly from the supplied paper identifier or title.",
            )
        )

    for concept in request.concept_inputs:
        matches = provider.search_papers(concept, limit=1)
        if not matches:
            continue
        resolved.append(
            ResolvedSeed(
                input_type="concept",
                input_value=concept,
                resolution_kind="search_derived_seed",
                paper=matches[0],
                why_selected=f"Top search match for concept seed '{concept}'.",
            )
        )

    for question in request.question_inputs:
        matches = provider.search_papers(question, limit=1)
        if not matches:
            continue
        resolved.append(
            ResolvedSeed(
                input_type="question",
                input_value=question,
                resolution_kind="search_derived_seed",
                paper=matches[0],
                why_selected=f"Top search match for question seed '{question}'.",
            )
        )

    deduped: dict[str, ResolvedSeed] = {}
    for seed in resolved:
        deduped.setdefault(seed.paper.paper_id, seed)
    return list(deduped.values())


def _expand_candidates(
    request: DiscoveryRequest,
    provider: DiscoveryProvider,
    resolved_seeds: list[ResolvedSeed],
) -> tuple[list[CitationEdge], set[str]]:
    candidate_ids: set[str] = set()
    edges: dict[tuple[str, str, str], CitationEdge] = {}

    frontier = {seed.paper.paper_id for seed in resolved_seeds}
    seed_ids = set(frontier)

    for _ in range(request.forward_depth):
        next_frontier: set[str] = set()
        for paper_id in frontier:
            for paper in provider.get_forward_citations(paper_id):
                next_frontier.add(paper.paper_id)
                candidate_ids.add(paper.paper_id)
                key = (paper_id, paper.paper_id, "forward")
                edges[key] = CitationEdge(
                    source_paper_id=paper_id,
                    target_paper_id=paper.paper_id,
                    direction="forward",
                    reason=provider.get_edge_reason(paper_id, paper.paper_id, "forward"),
                )
        frontier = next_frontier

    frontier = set(seed_ids)
    for _ in range(request.reverse_depth):
        next_frontier = set()
        for paper_id in frontier:
            for paper in provider.get_reverse_citations(paper_id):
                next_frontier.add(paper.paper_id)
                candidate_ids.add(paper.paper_id)
                key = (paper.paper_id, paper_id, "reverse")
                edges[key] = CitationEdge(
                    source_paper_id=paper.paper_id,
                    target_paper_id=paper_id,
                    direction="reverse",
                    reason=provider.get_edge_reason(paper.paper_id, paper_id, "reverse"),
                )
        frontier = next_frontier

    candidate_ids.difference_update(seed_ids)
    return sorted(edges.values(), key=lambda edge: (edge.direction, edge.source_paper_id, edge.target_paper_id)), candidate_ids


def _rank_candidates(
    request: DiscoveryRequest,
    provider: DiscoveryProvider,
    resolved_seeds: list[ResolvedSeed],
    candidate_ids: set[str],
) -> list[RankedCandidate]:
    seed_term_pool = _seed_terms(request, resolved_seeds)
    seed_author_pool = {author for seed in resolved_seeds for author in seed.paper.authors}
    citation_link_map = _citation_link_map(request, provider, resolved_seeds, candidate_ids)

    ranked: list[RankedCandidate] = []
    for candidate_id in candidate_ids:
        paper = provider.resolve_paper(candidate_id)
        if request.year_min is not None and paper.year < request.year_min:
            continue

        haystack = " ".join([paper.title, paper.abstract, *paper.keywords])
        terms = tokenize(haystack)

        if request.must_match and not all(term.casefold() in terms for term in [item.casefold() for item in request.must_match]):
            continue
        if any(term.casefold() in terms for term in [item.casefold() for item in request.exclude]):
            continue

        matched_terms = sorted(seed_term_pool & terms)
        citation_links = citation_link_map.get(candidate_id, [])
        author_overlap = sorted(seed_author_pool & set(paper.authors))

        score = 0.0
        score += len(citation_links) * 3.0
        score += len(matched_terms) * 1.25
        score += max(paper.year - 2020, 0) * 0.2
        score += len(author_overlap) * 0.75

        reasons = []
        if citation_links:
            reasons.append(f"Connected to seed papers through {len(citation_links)} citation edge(s).")
        if matched_terms:
            reasons.append(f"Matches seed context terms: {', '.join(matched_terms[:5])}.")
        if author_overlap:
            reasons.append(f"Shares author context with seed set: {', '.join(author_overlap)}.")
        reasons.append(f"Recency contribution from publication year {paper.year}.")

        ranked.append(
            RankedCandidate(
                paper=paper,
                score=round(score, 2),
                ranking_reasons=reasons,
                matched_terms=matched_terms,
                citation_links_to_seeds=citation_links,
            )
        )

    ranked.sort(key=lambda item: (-item.score, -item.paper.year, item.paper.paper_id))
    return ranked[: request.max_candidates]


def _seed_terms(request: DiscoveryRequest, resolved_seeds: list[ResolvedSeed]) -> set[str]:
    direct_terms = set()
    for value in [*request.concept_inputs, *request.question_inputs]:
        direct_terms.update(tokenize(value))
    for seed in resolved_seeds:
        direct_terms.update(tokenize(seed.paper.title))
        direct_terms.update(seed.paper.keywords)
    return {term.casefold() for term in direct_terms}


def _citation_link_map(
    request: DiscoveryRequest,
    provider: DiscoveryProvider,
    resolved_seeds: list[ResolvedSeed],
    candidate_ids: set[str],
) -> dict[str, list[str]]:
    seed_ids = {seed.paper.paper_id for seed in resolved_seeds}
    links: dict[str, list[str]] = defaultdict(list)

    for seed_id in seed_ids:
        if request.forward_depth:
            frontier = {seed_id}
            for _ in range(request.forward_depth):
                next_frontier = set()
                for paper_id in frontier:
                    for paper in provider.get_forward_citations(paper_id):
                        next_frontier.add(paper.paper_id)
                        if paper.paper_id in candidate_ids:
                            links[paper.paper_id].append(f"{paper_id} -> {paper.paper_id}")
                frontier = next_frontier
        if request.reverse_depth:
            frontier = {seed_id}
            for _ in range(request.reverse_depth):
                next_frontier = set()
                for paper_id in frontier:
                    for paper in provider.get_reverse_citations(paper_id):
                        next_frontier.add(paper.paper_id)
                        if paper.paper_id in candidate_ids:
                            links[paper.paper_id].append(f"{paper.paper_id} -> {paper_id}")
                frontier = next_frontier

    for candidate_id in list(links):
        links[candidate_id] = sorted(set(links[candidate_id]))
    return links
