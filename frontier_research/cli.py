from __future__ import annotations

import argparse
import json

from frontier_research.discovery import run_discovery
from frontier_research.models import DiscoveryRequest
from frontier_research.providers import DemoDiscoveryProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="frontier-research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="Run the discovery CLI slice.")
    discover.add_argument("--paper", action="append", default=[], help="Direct paper seed identifier or exact title.")
    discover.add_argument("--concept", action="append", default=[], help="Concept seed used to derive paper seeds.")
    discover.add_argument("--question", action="append", default=[], help="Research question seed used to derive paper seeds.")
    discover.add_argument("--forward-depth", type=int, default=1, help="Number of forward citation hops to expand.")
    discover.add_argument("--reverse-depth", type=int, default=1, help="Number of reverse citation hops to expand.")
    discover.add_argument("--must-match", action="append", default=[], help="Keyword filter all candidates must contain.")
    discover.add_argument("--exclude", action="append", default=[], help="Keyword filter that removes matching candidates.")
    discover.add_argument("--year-min", type=int, default=None, help="Minimum publication year for candidate papers.")
    discover.add_argument("--max-candidates", type=int, default=10, help="Maximum number of candidates in output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "discover":
        parser.error(f"Unsupported command: {args.command}")

    request = DiscoveryRequest(
        paper_inputs=args.paper,
        concept_inputs=args.concept,
        question_inputs=args.question,
        forward_depth=max(args.forward_depth, 0),
        reverse_depth=max(args.reverse_depth, 0),
        max_candidates=max(args.max_candidates, 1),
        must_match=args.must_match,
        exclude=args.exclude,
        year_min=args.year_min,
    )
    result = run_discovery(request, DemoDiscoveryProvider())
    print(json.dumps(result.to_dict(), indent=2))
    return 0
