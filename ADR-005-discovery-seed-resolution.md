# ADR-005: Discovery Seed Resolution and Canonical Seed Records

**Status:** Proposed
**Date:** 2026-04-05
**Deciders:** Neill Killgore

## Context

ADR-004 defines the public `frontier discover run` contract and says every discovery invocation emits `resolved_seeds[]` in a canonical run document. The next ambiguity is how mixed seed inputs actually become that canonical seed list.

The first discovery slice accepts three researcher-facing seed types:

- direct paper identifiers
- concept text
- research-question text

Those inputs do not resolve the same way:

- paper inputs should resolve directly to one canonical paper or produce a clear failure
- concept inputs usually expand through search into one or more candidate seed papers
- research-question inputs also expand through search, but their provenance needs to preserve the original question text

Without an explicit seed-resolution contract, the implementation will drift on several load-bearing behaviors:

1. Duplicate papers reached through different input paths may be double-counted.
2. Search-derived seeds may lose the reason they were included.
3. Ambiguous or invalid inputs may either fail the whole run or disappear silently.
4. Downstream citation expansion and scoring code may receive inconsistent seed objects.

The Linear issue for this ADR requires four things:

- one canonical seed list from mixed inputs
- direct vs. search-derived provenance on each seed
- deduplication without provenance loss
- clear reporting for invalid or ambiguous inputs alongside successful resolutions

## Decision

**Normalize all incoming seed arguments into `seed_requests[]`, resolve them through a staged pipeline, merge equivalent papers into one canonical `resolved_seed` per paper, and preserve every successful and failed path as structured provenance.**

This decision complements ADR-004 by freezing the semantics of `resolved_seeds[]`, the partial-failure model, and the deduplication contract for the first discovery slice.

## Resolution Pipeline

Every discovery run resolves seeds in five stages:

1. **Normalize inputs**
   Convert CLI flags into typed `seed_requests[]` records with stable IDs.
2. **Resolve direct paper inputs**
   Attempt identifier parsing and canonical paper lookup.
3. **Expand concept and question inputs**
   Use provider search to derive candidate seed papers from text inputs.
4. **Merge equivalent papers**
   Collapse duplicates into one canonical seed record per paper.
5. **Emit structured outcome**
   Return canonical `resolved_seeds[]` plus warnings/errors for unresolved paths.

The pipeline is intentionally additive. A failed input path must not erase successful resolutions from the same run.

## Canonical Input Model

Before resolution, every researcher-supplied seed becomes a `seed_request`:

```json
{
  "request_id": "req_01",
  "input_type": "paper",
  "input": "doi:10.48550/arXiv.1706.03762",
  "position": 0
}
```

Required fields:

| Field | Type | Meaning |
|------|------|---------|
| `request_id` | string | Stable identifier for this input path within the run. |
| `input_type` | enum | `paper`, `concept`, or `question`. |
| `input` | string | Original researcher-supplied value. |
| `position` | integer | Original ordering in the request for deterministic reporting. |

Rules:

- `input` is preserved exactly as entered by the researcher.
- `position` preserves ordering for human-readable explanations and deterministic snapshots.
- `request_id` is the anchor for all downstream provenance, warnings, and errors.

## Resolution Semantics by Input Type

### Paper inputs

Paper inputs represent direct intent. The resolver should:

1. Parse the identifier shape when possible.
2. Attempt canonical lookup using supported identifiers such as DOI, arXiv ID, Semantic Scholar paper ID, or provider URL.
3. Return exactly one canonical paper on success.

Paper inputs must not fan out into multiple resolved seeds. If lookup returns multiple plausible papers, the outcome is ambiguous and the request remains unresolved.

### Concept inputs

Concept inputs represent thematic intent, not a canonical paper. The resolver should:

1. Search the provider using the concept text.
2. Select zero or more candidate papers according to provider ranking and first-slice heuristics.
3. Record why each derived paper was accepted as a seed.

Concept inputs may yield multiple resolved seeds or none.

### Question inputs

Question inputs behave like concept inputs with stronger provenance requirements. The resolver should:

1. Search the provider using the question text.
2. Select zero or more papers that best instantiate the question as discovery seeds.
3. Preserve the exact question text in provenance so later scoring and explanation code can refer back to it.

Question inputs may yield multiple resolved seeds or none.

## Canonical Resolved Seed Record

After merge and deduplication, each unique paper becomes one `resolved_seed` record:

```json
{
  "seed_id": "seed_01",
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
  "seed_kind": "direct",
  "source_paths": [
    {
      "request_id": "req_01",
      "input_type": "paper",
      "input": "doi:10.48550/arXiv.1706.03762",
      "resolution_kind": "direct_lookup",
      "matched_by": "doi",
      "provider": "semantic-scholar"
    },
    {
      "request_id": "req_03",
      "input_type": "concept",
      "input": "transformer architectures",
      "resolution_kind": "search_derived",
      "matched_by": "provider_search",
      "provider": "semantic-scholar",
      "rank": 2,
      "match_confidence": 0.73
    }
  ],
  "provenance_summary": {
    "is_direct_input": true,
    "is_search_derived": true,
    "request_count": 2
  }
}
```

### Required fields

| Field | Type | Meaning |
|------|------|---------|
| `seed_id` | string | Stable identifier for the canonical resolved seed in this run. |
| `paper` | object | Minimal abstract-visible paper metadata used by the discovery slice. |
| `seed_kind` | enum | `direct`, `derived`, or `mixed`. |
| `source_paths` | array | Every successful input path that led to this paper. |
| `provenance_summary` | object | Compact summary for filtering and explanation logic. |

### `seed_kind` rules

- `direct` means the paper was reached only from direct paper input.
- `derived` means the paper was reached only from concept or question search.
- `mixed` means the same paper was reached through both direct and search-derived paths.

This field satisfies the acceptance criterion that every seed records whether it was direct input or search-derived, while still handling merged duplicates honestly.

## Dedupe Rules

The dedupe unit is the canonical paper, not the input path.

Equivalent papers must merge when they share a stable canonical identity in this priority order:

1. provider canonical paper ID
2. DOI
3. arXiv ID
4. normalized provider URL

If none of those identifiers are available, the resolver may fall back to a normalized metadata fingerprint using title, year, and first author, but the merged record must include a warning because that match is weaker.

When duplicates merge:

- keep one `resolved_seed`
- append all successful `source_paths`
- recompute `seed_kind`
- preserve the strongest available canonical identifiers in `paper`

The merge must never discard provenance. Losing the second or third path to the same paper is a correctness bug because later ranking and explanation logic depends on how the paper was reached.

## Search-Derived Path Metadata

For concept and question inputs, each successful `source_path` should preserve enough context to explain why a paper became a seed. The first slice requires:

| Field | Type | Meaning |
|------|------|---------|
| `rank` | integer | Provider result rank before dedupe. |
| `match_confidence` | number or null | Provider or heuristic confidence when available. |
| `matched_by` | string | Usually `provider_search`, but extensible for future heuristics. |
| `reason` | string or null | Optional short explanation for human-facing review. |

Question-derived paths should additionally preserve the original question text in the shared `input` field from `seed_request`.

## Invalid and Ambiguous Inputs

Seed resolution is allowed to be partially successful. Failures belong to the input path, not automatically to the whole run.

### Invalid inputs

An input is invalid when it cannot be parsed or cannot produce any acceptable provider lookup or search result.

Example:

```json
{
  "code": "paper_identifier_invalid",
  "request_id": "req_02",
  "input_type": "paper",
  "input": "doi:not-a-real-id",
  "message": "Paper input is not a valid supported identifier.",
  "severity": "error",
  "retryable": false
}
```

### Ambiguous inputs

An input is ambiguous when the resolver finds multiple plausible matches but cannot justify selecting one canonical paper.

Example:

```json
{
  "code": "paper_identifier_ambiguous",
  "request_id": "req_04",
  "input_type": "paper",
  "input": "attention paper",
  "message": "Input matched multiple papers and needs a more specific identifier.",
  "severity": "error",
  "retryable": true,
  "candidates": [
    "s2:abc123",
    "s2:def456"
  ]
}
```

Rules:

- unresolved direct paper inputs are errors, not warnings
- empty concept or question expansions are warnings unless they indicate provider failure
- provider outages or transport failures are errors and may set the run status to `failed` if no seeds resolve
- successful seeds must still be returned when other inputs fail

## Run Status Rules

ADR-004 defines `status` as `success`, `partial`, or `failed`. Seed resolution determines those values as follows:

- `success` when every input path either resolved as expected or was intentionally empty with no material warnings
- `partial` when at least one seed resolved and at least one input path produced an error or material warning
- `failed` when no seeds resolved and the request cannot proceed to citation expansion

This keeps the failure model aligned with the issue requirement to report bad inputs without losing successful ones.

## Downstream Contract

After resolution finishes, downstream discovery stages may assume:

1. `resolved_seeds[]` contains unique canonical papers.
2. Each seed exposes minimal abstract-visible paper metadata only.
3. Each seed preserves all successful provenance paths.
4. Warnings and errors are attached to `request_id` so they can be rendered next to the originating input.

Downstream citation expansion must use `seed_id` as the stable anchor for edge traversal and candidate provenance.

## Representative Example

Input request:

```bash
frontier discover run \
  --paper doi:10.48550/arXiv.1706.03762 \
  --concept "transformer architectures" \
  --question "Which papers challenge chain-of-thought reliability?" \
  --expand both
```

Resolution outcome summary:

- the direct paper resolves to one canonical paper
- the concept search returns that same paper plus two others
- the question search returns one overlapping paper plus one new paper
- one malformed paper identifier from another request would appear as an error without deleting the successful seeds

Canonical result:

- four `seed_requests`
- three unique `resolved_seeds`
- one merged seed marked `mixed`
- one invalid-input error, if applicable

## Options Considered

### Option A: Merge by canonical paper and preserve all paths (chosen)

Pros:

- satisfies dedupe and provenance requirements together
- gives downstream ranking richer context
- matches how researchers think about "the same paper reached in multiple ways"

Cons:

- requires more bookkeeping than a flat list

### Option B: Keep one resolved seed per input path

Pros:

- simple to implement
- no merge logic needed

Cons:

- duplicate papers leak into expansion and scoring
- downstream tools need to dedupe repeatedly
- provenance becomes fragmented

### Option C: Fail the whole run on the first bad input

Pros:

- simplest error model

Cons:

- violates the product requirement for mixed-input resilience
- wastes successful resolutions from the same run

## Consequences

- **Easier:** citation expansion, candidate scoring, and review UIs receive one stable seed object model with explicit provenance.
- **Harder:** the first implementation needs disciplined identity matching and per-request error reporting.
- **Revisit:** once the product adds interactive disambiguation or researcher approval loops, ambiguous inputs may become reviewable pending items instead of immediate errors.

## Action Items

1. [ ] Implement `seed_requests[]` normalization inside `frontier discover run`
2. [ ] Define the `resolved_seed` JSON schema and validate it in the canonical run document
3. [ ] Implement canonical paper identity matching using provider ID, DOI, arXiv ID, and normalized URL
4. [ ] Implement merge logic that preserves every successful `source_path`
5. [ ] Implement per-request warnings and errors with stable `request_id` references
6. [ ] Document first-slice heuristics for concept and question search result selection
