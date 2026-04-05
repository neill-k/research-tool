from __future__ import annotations

import json
import subprocess
import sys
import unittest

from frontier_research.vertical_discovery import run_discovery
from frontier_research.models import DiscoveryRequest
from frontier_research.providers import DemoDiscoveryProvider


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DemoDiscoveryProvider()

    def test_mixed_seed_resolution_distinguishes_direct_and_search_derived(self) -> None:
        result = run_discovery(
            DiscoveryRequest(
                paper_inputs=["paper:attention"],
                concept_inputs=["retrieval"],
                question_inputs=["Which papers connect retrieval with agent memory?"],
            ),
            self.provider,
        )

        resolution_kinds = {seed.resolution_kind for seed in result.resolved_seeds}
        self.assertIn("direct_paper_seed", resolution_kinds)
        self.assertIn("search_derived_seed", resolution_kinds)
        self.assertTrue(result.candidate_papers)

    def test_forward_and_reverse_toggles_change_expansion(self) -> None:
        forward_only = run_discovery(
            DiscoveryRequest(paper_inputs=["paper:attention"], concept_inputs=[], question_inputs=[], forward_depth=1, reverse_depth=0),
            self.provider,
        )
        reverse_only = run_discovery(
            DiscoveryRequest(paper_inputs=["paper:memory-rag"], concept_inputs=[], question_inputs=[], forward_depth=0, reverse_depth=1),
            self.provider,
        )

        self.assertTrue(any(edge.direction == "forward" for edge in forward_only.citation_edges))
        self.assertFalse(any(edge.direction == "reverse" for edge in forward_only.citation_edges))
        self.assertTrue(any(edge.direction == "reverse" for edge in reverse_only.citation_edges))
        self.assertFalse(any(edge.direction == "forward" for edge in reverse_only.citation_edges))

    def test_filters_and_ranking_reasons_are_emitted(self) -> None:
        result = run_discovery(
            DiscoveryRequest(
                paper_inputs=["paper:attention"],
                concept_inputs=["retrieval"],
                question_inputs=[],
                must_match=["retrieval"],
                exclude=["survey"],
                year_min=2023,
            ),
            self.provider,
        )

        self.assertTrue(result.candidate_papers)
        for candidate in result.candidate_papers:
            corpus = " ".join([candidate.paper.title, candidate.paper.abstract, *candidate.paper.keywords]).casefold()
            self.assertIn("retrieval", corpus)
            self.assertNotIn("survey", corpus)
            self.assertGreaterEqual(candidate.paper.year, 2023)
            self.assertTrue(candidate.ranking_reasons)

    def test_cli_outputs_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "frontier_research",
                "discover",
                "--paper",
                "paper:attention",
                "--concept",
                "retrieval",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertIn("resolved_seeds", payload)
        self.assertIn("candidate_papers", payload)


if __name__ == "__main__":
    unittest.main()
