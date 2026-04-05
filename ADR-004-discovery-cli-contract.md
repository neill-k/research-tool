# ADR-004: Discovery CLI Contract and Canonical Run Schema

**Status:** Proposed
**Date:** 2026-04-04
**Deciders:** Neill Killgore

## Context

The first Frontier Research discovery slice needs a stable command-line contract before implementation work fans out into seed resolution, citation expansion, scoring, and downstream review tooling.

Without an explicit contract, the first implementation risks hidden behavior:

1. Seed input types drift across commands.
2. Citation expansion settings become implicit defaults instead of explicit researcher choices.
3. Criteria handling becomes ad hoc and hard to reproduce.
4. Downstream tools cannot rely on a canonical machine-readable output shape.

Existing ADRs already define relevant constraints:

- ADR-001 says operational state should be stored as plain-text JSON or JSONL sidecars.
- ADR-003 says Sources are shared globally and claims, citation edges, and runs need durable identifiers and provenance.

This ADR defines the public CLI surface for discovery runs and the canonical run schema that all first-pass discovery implementations must emit.

## Decision

**Use a single `frontier discover run` command as the primary discovery entry point. Require explicit flags for seeds, criteria, citation expansion, and output behavior. Emit one canonical run document for every invocation, regardless of human-readable output mode.**

### Command surface

The primary command is:

```bash
frontier discover run [options]
```

The command accepts mixed seed types in one invocation:

- `--paper <identifier>` for direct paper identifiers
- `--concept <text>` for concept-led discovery seeds
- `--question <text>` for research-question-led discovery seeds

The command may be repeated for each seed type:

```bash
frontier discover run \
  --paper doi:10.48550/arXiv.1706.03762 \
  --paper arxiv:2303.08774 \
  --concept "test-time scaling laws" \
  --question "Which recent papers challenge chain-of-thought gains on hard reasoning benchmarks?"
```

### Required behavior

1. At least one seed flag must be present.
2. Citation expansion must be explicit at invocation time.
3. Criteria input must be explicit when used; no hidden profile-specific criteria files.
4. Every invocation must produce a canonical run document, even if the terminal output is text.
5. Human-readable output is a rendering of the canonical run document, not a separate result shape.

## CLI Contract

### Positional shape

There are no positional arguments after `frontier discover run`. All researcher intent is expressed through named flags so runs remain self-documenting in shell history and automation logs.

### Options

| Flag | Type | Repeatable | Required | Meaning |
|------|------|------------|----------|---------|
| `--paper <identifier>` | string | yes | no | Add a direct paper seed such as DOI, arXiv ID, Semantic Scholar paper ID, or provider URL. |
| `--concept <text>` | string | yes | no | Add a concept seed that should be resolved into candidate source papers. |
| `--question <text>` | string | yes | no | Add a research-question seed that should be resolved into candidate source papers. |
| `--frontier <frontier-id>` | string | no | no | Associate the run with an existing Frontier. Optional for the first slice but reserved now for stable automation usage. |
| `--criteria <path>` | path | no | no | Path to a criteria file describing inclusion, exclusion, and ranking preferences. |
| `--expand <mode>` | enum | no | yes | Citation expansion mode: `none`, `backward`, `forward`, or `both`. |
| `--max-hops <n>` | integer | no | no | Maximum citation depth from resolved seed papers. Default `1`. |
| `--max-candidates <n>` | integer | no | no | Hard cap on returned candidate papers after scoring and filtering. Default `50`. |
| `--provider <name>` | string | no | no | Discovery provider override. If omitted, use workspace default. |
| `--format <mode>` | enum | no | no | Terminal output mode: `text`, `json`, or `jsonl`. Default `text`. |
| `--output <path>` | path | no | no | Write the canonical run output to a file instead of stdout. |
| `--run-id <id>` | string | no | no | Caller-supplied run identifier for reproducible automation and retries. |

### Validation rules

- At least one of `--paper`, `--concept`, or `--question` is required.
- `--expand` is required because citation expansion is an intentional researcher choice.
- `--max-hops` must be greater than or equal to `0`.
- `--max-candidates` must be greater than `0`.
- `--format jsonl` is valid only when rendering a candidate-oriented projection; the underlying canonical run document still exists as structured JSON.
- If `--output` is omitted, the command writes the selected rendering to stdout and still persists the canonical run document in `.frontier/runs/{run-id}.json`.

## Canonical Run Schema

Every invocation emits one canonical JSON document with the following top-level shape:

```json
{
  "run_id": "discover_2026-04-04T12-00-00Z_01",
  "command": {
    "name": "frontier discover run",
    "argv": [
      "--paper",
      "doi:10.48550/arXiv.1706.03762",
      "--question",
      "Which recent papers challenge chain-of-thought gains on hard reasoning benchmarks?",
      "--expand",
      "both",
      "--criteria",
      "criteria/reasoning.json",
      "--format",
      "json"
    ]
  },
  "request": {
    "frontier_id": null,
    "provider": "semantic-scholar",
    "seed_inputs": {
      "papers": [
        {
          "input": "doi:10.48550/arXiv.1706.03762",
          "input_type": "paper"
        }
      ],
      "concepts": [],
      "questions": [
        {
          "input": "Which recent papers challenge chain-of-thought gains on hard reasoning benchmarks?",
          "input_type": "question"
        }
      ]
    },
    "criteria": {
      "source": "criteria/reasoning.json",
      "loaded": true
    },
    "citation_expansion": {
      "mode": "both",
      "max_hops": 1
    },
    "limits": {
      "max_candidates": 50
    }
  },
  "resolved_seeds": [],
  "candidates": [],
  "citation_edges": [],
  "warnings": [],
  "errors": [],
  "stats": {
    "seed_count": 2,
    "resolved_seed_count": 0,
    "candidate_count": 0,
    "citation_edge_count": 0
  },
  "status": "success",
  "created_at": "2026-04-04T12:00:00Z"
}
```

### Top-level fields

| Field | Type | Meaning |
|------|------|---------|
| `run_id` | string | Stable identifier for the discovery run. |
| `command` | object | Reproducible command metadata including normalized argv. |
| `request` | object | Normalized request payload after CLI parsing. |
| `resolved_seeds` | array | Canonical seed records after identifier resolution or concept/question search. |
| `candidates` | array | Scored candidate papers returned by discovery. |
| `citation_edges` | array | Directed citation graph edges traversed during expansion. |
| `warnings` | array | Non-fatal issues that may affect trust or completeness. |
| `errors` | array | Fatal or per-input failures. |
| `stats` | object | Aggregated counts and summary metrics. |
| `status` | enum | `success`, `partial`, or `failed`. |
| `created_at` | string | ISO-8601 timestamp for the run document. |

### `resolved_seeds[]`

Each resolved seed record must include:

```json
{
  "seed_id": "seed_01",
  "source_input": {
    "input": "doi:10.48550/arXiv.1706.03762",
    "input_type": "paper"
  },
  "resolution_kind": "direct_paper",
  "paper": {
    "paper_id": "s2:204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
    "authors": [
      "Ashish Vaswani",
      "Noam Shazeer"
    ],
    "venue": "NeurIPS",
    "year": 2017,
    "doi": "10.48550/arXiv.1706.03762",
    "arxiv_id": "1706.03762"
  },
  "provenance": {
    "provider": "semantic-scholar",
    "matched_by": "doi"
  }
}
```

Rules:

- Direct paper inputs resolve to one canonical paper or an error.
- Concept and question inputs may resolve to multiple seed papers.
- The original user input is always preserved in `source_input`.

### `candidates[]`

Each candidate record must include:

```json
{
  "paper_id": "s2:abc123",
  "title": "Example Candidate Paper",
  "abstract": "Candidate abstract-visible summary...",
  "authors": [
    "Jane Doe"
  ],
  "venue": "ICLR",
  "year": 2025,
  "doi": null,
  "arxiv_id": "2501.01234",
  "discovery": {
    "reached_from_seed_ids": [
      "seed_01"
    ],
    "expansion_paths": [
      {
        "from_paper_id": "s2:204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        "to_paper_id": "s2:abc123",
        "direction": "forward",
        "hops": 1
      }
    ]
  },
  "score": {
    "value": 0.82,
    "reasons": [
      {
        "label": "question_match",
        "weight": 0.45,
        "explanation": "Matches the explicit question's focus on chain-of-thought reliability."
      },
      {
        "label": "citation_proximity",
        "weight": 0.22,
        "explanation": "Reached in one hop from a direct seed paper."
      }
    ]
  },
  "criteria_matches": {
    "included_by": [
      "reasoning-benchmark-paper"
    ],
    "excluded_by": []
  }
}
```

Rules:

- Candidate metadata is limited to abstract-visible fields in the first discovery slice.
- Scoring reasons are first-class structured fields, not free-form markdown.
- Candidate records must be stable enough for downstream scout and review workflows to consume directly.

### `citation_edges[]`

Each traversed citation edge must include:

```json
{
  "edge_id": "edge_01",
  "from_paper_id": "s2:204e3073870fae3d05bcbc2f6a8e263d9b72e776",
  "to_paper_id": "s2:abc123",
  "direction": "forward",
  "provider": "semantic-scholar",
  "context": null,
  "hops_from_seed": 1
}
```

Rules:

- `direction` is always relative to the seed traversal step: `forward` means cited-by expansion, `backward` means references expansion.
- If the provider exposes citation intent or context, it belongs in `context`.

### `warnings[]` and `errors[]`

Warnings and errors use the same shape:

```json
{
  "code": "concept_seed_low_confidence",
  "message": "Concept seed resolved through low-confidence search matches.",
  "input": "test-time scaling laws",
  "retryable": false
}
```

Rules:

- Warnings do not fail the run.
- Fatal setup errors set `status` to `failed`.
- Mixed success across seeds sets `status` to `partial`.

## Criteria File Contract

The `--criteria` file must resolve to JSON or YAML that normalizes into this logical shape:

```json
{
  "include": [
    "reasoning benchmarks",
    "evaluation reliability"
  ],
  "exclude": [
    "survey papers only"
  ],
  "rank": [
    {
      "label": "benchmark_novelty",
      "weight": 0.4
    },
    {
      "label": "seed_similarity",
      "weight": 0.6
    }
  ]
}
```

The first slice does not standardize the full authoring format beyond these three normalized concepts:

- inclusion filters
- exclusion filters
- ranking preferences

The CLI contract standardizes the normalized in-memory representation and the canonical run schema field, not the long-term authoring DSL.

## Proposed `--help` Output

The implemented command help should be substantially equivalent to:

```text
Usage:
  frontier discover run [options]

Seed inputs:
  --paper <identifier>     Add a direct paper seed (repeatable)
  --concept <text>         Add a concept seed (repeatable)
  --question <text>        Add a research-question seed (repeatable)

Discovery behavior:
  --expand <mode>          Citation expansion mode: none|backward|forward|both
  --max-hops <n>           Maximum citation depth (default: 1)
  --max-candidates <n>     Maximum returned candidates after scoring (default: 50)
  --criteria <path>        Criteria file for inclusion, exclusion, and ranking
  --provider <name>        Override the discovery provider
  --frontier <frontier-id> Associate the run with an existing Frontier

Output:
  --format <mode>          Render as text|json|jsonl (default: text)
  --output <path>          Write rendered output to a file
  --run-id <id>            Supply a caller-defined run identifier

Notes:
  At least one seed flag is required.
  --expand is required.
  Every invocation emits a canonical run document.
```

## Representative Invocation

```bash
frontier discover run \
  --paper doi:10.48550/arXiv.2201.11903 \
  --concept "self-improving evaluation agents" \
  --question "What papers from the last two years improve literature-review reliability with citation-grounded retrieval?" \
  --expand both \
  --max-hops 1 \
  --max-candidates 25 \
  --criteria criteria/lit-review-reliability.yaml \
  --format json \
  --output runs/discovery-example.json
```

This invocation demonstrates the expected workflow:

- mixed seed inputs
- explicit citation expansion
- explicit criteria selection
- machine-readable output
- caller-visible output destination

## Output Persistence Rules

- The canonical run document persists to `.frontier/runs/{run-id}.json`.
- If `--output` is supplied with `--format json`, the written file may be byte-for-byte identical to the canonical run document.
- If `--format text` or `--format jsonl` is selected, the persisted `.frontier/runs/{run-id}.json` remains the source of truth and the requested output is a derived rendering.

## Options Considered

### Option A: One explicit `discover run` command with named flags (chosen)

Pros:

- Stable automation surface.
- Easy to reproduce from shell history.
- Clear room for mixed seed inputs.

Cons:

- More verbose than subcommands with positionals.

### Option B: Separate commands per seed type

Examples:

- `frontier discover paper ...`
- `frontier discover concept ...`
- `frontier discover question ...`

Pros:

- Slightly simpler parser per command.

Cons:

- Mixed-seed runs become awkward.
- Output contracts drift across commands.

### Option C: Hidden defaults for expansion and criteria

Pros:

- Shorter commands.

Cons:

- Reproducibility degrades.
- Researcher intent becomes implicit.
- Automation and debugging become brittle.

## Consequences

- **Easier:** Seed resolution, citation expansion, scoring, and downstream review work now share one public request and response contract.
- **Harder:** The first implementation must normalize several user-facing flag combinations into one stable schema.
- **Revisit:** Once real criteria files and provider differences exist, the criteria authoring DSL and provider override semantics may need a follow-up ADR. This ADR only freezes the CLI contract and normalized run shape.

## Action Items

1. [ ] Implement `frontier discover run` with the flags defined here
2. [ ] Define JSON schema validation for the canonical run document
3. [ ] Define normalization rules for criteria YAML and JSON inputs
4. [ ] Implement persistence to `.frontier/runs/{run-id}.json`
5. [ ] Implement text and JSONL renderers as views over the canonical run document
6. [ ] Add the representative example to the future CLI README or docs site once the binary exists
