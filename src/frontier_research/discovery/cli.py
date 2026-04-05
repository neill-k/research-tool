from __future__ import annotations

import argparse
import json
from pathlib import Path

from frontier_research.discovery.models import DiscoveryRun, PaperRole
from frontier_research.discovery.providers import SemanticScholarMetadataProvider
from frontier_research.discovery.service import (
    CriteriaValidationError,
    DiscoveryService,
    parse_criteria,
)


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

    expand_parser = subparsers.add_parser(
        "expand",
        help="Expand forward references and reverse citations from resolved seed papers.",
    )
    expand_parser.add_argument(
        "identifiers",
        nargs="+",
        help="One or more resolved paper identifiers accepted by the provider.",
    )
    expand_parser.add_argument(
        "--forward-limit",
        type=int,
        default=10,
        help="Maximum number of forward references to fetch per seed paper.",
    )
    expand_parser.add_argument(
        "--reverse-limit",
        type=int,
        default=10,
        help="Maximum number of reverse citations to fetch per seed paper.",
    )
    expand_parser.add_argument(
        "--criteria-file",
        help="Path to a JSON file that defines filtering and ranking criteria.",
    )
    expand_parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Emit a machine-readable JSON artifact or a readable text summary.",
    )
    expand_parser.add_argument(
        "--output-file",
        help="Optional destination path for the rendered artifact.",
    )
    return parser


def render_run(run: DiscoveryRun, *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(run.to_dict(), indent=2, sort_keys=True)
    return render_text_run(run)


def render_text_run(run: DiscoveryRun) -> str:
    lines = [
        "Discovery Run",
        f"Provider: {run.run_metadata.provider}",
        f"Generated At: {run.run_metadata.generated_at}",
        "Request: "
        + ", ".join(run.run_metadata.request.identifiers)
        + f" (forward={run.run_metadata.request.forward_limit}, reverse={run.run_metadata.request.reverse_limit})",
        f"Seeds: {run.run_metadata.seed_count}",
        f"Candidates: {run.run_metadata.candidate_count}",
        f"Edges: {run.run_metadata.edge_count}",
        f"Warnings: {run.run_metadata.warning_count}",
    ]
    if run.run_metadata.request.criteria_source:
        lines.append(f"Criteria Source: {run.run_metadata.request.criteria_source}")

    lines.append("")
    lines.append("Resolved Seeds")
    for seed in run.seeds:
        title = seed.paper.title or seed.paper.provider_paper_id or "<untitled>"
        lines.append(
            f"- {title} [{seed.provenance.source_kind.value}: {seed.provenance.input_identifier}]"
        )

    lines.append("")
    lines.append("Candidates")
    if not run.candidates:
        lines.append("- None")
    for candidate in run.candidates:
        title = candidate.paper.title or candidate.paper.provider_paper_id or "<untitled>"
        if candidate.score is not None:
            lines.append(f"- {title} (score={candidate.score.total:.4f})")
        else:
            lines.append(f"- {title}")
        for provenance in candidate.provenance:
            lines.append(
                "  via "
                f"{provenance.direction.value} citation from seed {provenance.seed_paper_id}"
            )
        if candidate.score is not None and candidate.score.reasons:
            lines.append("  reasons: " + "; ".join(candidate.score.reasons))

    if run.warnings:
        lines.append("")
        lines.append("Warnings")
        for warning in run.warnings:
            lines.append(f"- {warning.code}: {warning.message}")

    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    provider = SemanticScholarMetadataProvider()
    service = DiscoveryService(provider=provider)

    if args.command == "fetch":
        metadata = service.fetch(identifier=args.identifier, role=PaperRole(args.role))
        print(json.dumps(metadata.to_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "expand":
        if args.forward_limit < 0 or args.reverse_limit < 0:
            parser.error("--forward-limit and --reverse-limit must be >= 0.")
        criteria = None
        if args.criteria_file:
            try:
                criteria = parse_criteria(
                    json.loads(Path(args.criteria_file).read_text(encoding="utf-8"))
                )
            except FileNotFoundError:
                parser.error(f"Criteria file not found: {args.criteria_file}")
            except json.JSONDecodeError as exc:
                parser.error(
                    f"Criteria file must contain valid JSON: {exc.msg} at line {exc.lineno}"
                )
            except CriteriaValidationError as exc:
                parser.error(f"Invalid discovery criteria: {exc}")
        run = service.expand(
            identifiers=args.identifiers,
            forward_limit=args.forward_limit,
            reverse_limit=args.reverse_limit,
            criteria=criteria,
            criteria_source=args.criteria_file,
        )
        rendered = render_run(run, output_format=args.output_format)
        if args.output_file:
            Path(args.output_file).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
