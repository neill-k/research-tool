from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from frontier_research.models import CitationEdge, Paper


class DiscoveryProvider(ABC):
    @abstractmethod
    def resolve_paper(self, paper_input: str) -> Paper:
        raise NotImplementedError

    @abstractmethod
    def search_papers(self, query: str, limit: int = 3) -> list[Paper]:
        raise NotImplementedError

    @abstractmethod
    def get_forward_citations(self, paper_id: str) -> list[Paper]:
        raise NotImplementedError

    @abstractmethod
    def get_reverse_citations(self, paper_id: str) -> list[Paper]:
        raise NotImplementedError

    @abstractmethod
    def get_edge_reason(self, source_paper_id: str, target_paper_id: str, direction: str) -> str:
        raise NotImplementedError


class DemoDiscoveryProvider(DiscoveryProvider):
    def __init__(self) -> None:
        self.papers = {
            "paper:attention": Paper(
                paper_id="paper:attention",
                title="Attention as a Retrieval Interface",
                abstract="Shows how attention-style retrieval improves memory access in agent pipelines.",
                year=2022,
                authors=["A. Singh", "R. Moore"],
                keywords=["attention", "retrieval", "agents", "memory"],
            ),
            "paper:memory-rag": Paper(
                paper_id="paper:memory-rag",
                title="Persistent Memory for Retrieval-Augmented Agents",
                abstract="Combines long-term memory with retrieval-augmented generation for planning agents.",
                year=2024,
                authors=["R. Moore", "L. Chen"],
                keywords=["retrieval", "agents", "memory", "rag"],
            ),
            "paper:litmaps": Paper(
                paper_id="paper:litmaps",
                title="Citation Expansion for Fast Literature Mapping",
                abstract="Uses backward and forward citation traversal to grow a research frontier quickly.",
                year=2023,
                authors=["N. Patel"],
                keywords=["literature", "citation", "discovery", "mapping"],
            ),
            "paper:benchmarking": Paper(
                paper_id="paper:benchmarking",
                title="Benchmarking Discovery Pipelines for Research Agents",
                abstract="Evaluates retrieval-aware ranking functions for paper recommendation in active research workflows.",
                year=2025,
                authors=["L. Chen", "P. Diaz"],
                keywords=["benchmark", "discovery", "ranking", "agents", "retrieval"],
            ),
            "paper:survey-memory": Paper(
                paper_id="paper:survey-memory",
                title="Survey of Memory Systems for LLM Agents",
                abstract="Surveys memory architectures, retrieval patterns, and citation-heavy agent workflows.",
                year=2021,
                authors=["J. Gomez"],
                keywords=["survey", "memory", "agents", "retrieval"],
            ),
            "paper:graphs": Paper(
                paper_id="paper:graphs",
                title="Question-Seeded Citation Graph Expansion",
                abstract="Starts from research questions and expands a graph of candidate papers with transparent ranking reasons.",
                year=2025,
                authors=["A. Singh", "N. Patel"],
                keywords=["questions", "citation", "graph", "ranking", "discovery"],
            ),
        }

        self.forward_edges = {
            "paper:attention": ["paper:memory-rag", "paper:graphs"],
            "paper:memory-rag": ["paper:benchmarking"],
            "paper:litmaps": ["paper:graphs", "paper:benchmarking"],
            "paper:survey-memory": ["paper:memory-rag"],
        }
        self.reverse_edges = defaultdict(list)
        for source_id, target_ids in self.forward_edges.items():
            for target_id in target_ids:
                self.reverse_edges[target_id].append(source_id)

    def resolve_paper(self, paper_input: str) -> Paper:
        if paper_input in self.papers:
            return self.papers[paper_input]

        lowered = paper_input.casefold()
        for paper in self.papers.values():
            if lowered == paper.title.casefold():
                return paper
        raise ValueError(f"Unknown paper seed: {paper_input}")

    def search_papers(self, query: str, limit: int = 3) -> list[Paper]:
        query_terms = _tokenize(query)
        scored: list[tuple[int, int, Paper]] = []
        for paper in self.papers.values():
            corpus_terms = set(_tokenize(" ".join([paper.title, paper.abstract, *paper.keywords])))
            overlap = len(query_terms & corpus_terms)
            if overlap:
                scored.append((overlap, paper.year, paper))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].paper_id))
        return [paper for _, _, paper in scored[:limit]]

    def get_forward_citations(self, paper_id: str) -> list[Paper]:
        return [self.papers[target_id] for target_id in self.forward_edges.get(paper_id, [])]

    def get_reverse_citations(self, paper_id: str) -> list[Paper]:
        return [self.papers[source_id] for source_id in self.reverse_edges.get(paper_id, [])]

    def get_edge_reason(self, source_paper_id: str, target_paper_id: str, direction: str) -> str:
        if direction == "forward":
            return f"{source_paper_id} cites {target_paper_id} in the demo citation graph"
        return f"{target_paper_id} is cited by {source_paper_id} in the demo citation graph"


def _tokenize(text: str) -> set[str]:
    stopwords = {
        "and",
        "for",
        "the",
        "with",
        "that",
        "this",
        "from",
        "which",
        "into",
    }
    return {
        part
        for part in "".join(ch if ch.isalnum() else " " for ch in text.casefold()).split()
        if len(part) > 2 and part not in stopwords
    }
