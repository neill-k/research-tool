from __future__ import annotations

import argparse
import json

from frontier_research.discovery.models import PaperRole
from frontier_research.discovery.providers import SemanticScholarMetadataProvider
from frontier_research.discovery.service import PaperMetadataService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frontier-discovery",
        description="Fetch normalized abstract-visible paper metadata.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch normalized paper metadata for a seed or candidate paper.",
    )
    fetch_parser.add_argument("identifier", help="Paper ID, DOI, Corpus ID, or URL")
    fetch_parser.add_argument(
        "--role",
        choices=[role.value for role in PaperRole],
        default=PaperRole.SEED.value,
        help="Whether the paper is a seed or discovered candidate.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        provider = SemanticScholarMetadataProvider()
        service = PaperMetadataService(provider=provider)
        metadata = service.fetch(identifier=args.identifier, role=PaperRole(args.role))
        print(json.dumps(metadata.to_dict(), indent=2, sort_keys=True))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
