# Frontier Research

Frontier Research is a researcher-controlled operating system for literature discovery, triage, synthesis, and experiment planning.

This repository currently includes the first discovery slices for `NEI-292`, `NEI-293`, `NEI-294`, and `NEI-295`: minimal metadata extraction, bidirectional citation expansion, researcher-defined ranking criteria, and stable discovery artifacts for downstream scout and review workflows.

## Install

```bash
python -m pip install -e ".[dev]"
```

## CLI

Fetch a paper by Semantic Scholar paper ID, Corpus ID, DOI, or another identifier accepted by the provider:

```bash
frontier-discovery fetch 10.1145/3442188.3445922 --role seed
```

Output is normalized JSON with explicit `missing_fields` entries when the provider omits values.

Expand forward references and reverse citations from one or more resolved seed papers:

```bash
frontier-discovery expand 10.1145/3442188.3445922 --forward-limit 5 --reverse-limit 5
```

The default JSON artifact includes:

- `run_metadata` with request inputs, generation time, counts, and partial-failure flag
- resolved `seeds` with explicit provenance
- deduplicated `candidates` with explicit citation provenance
- `edges` with citation `direction`, contexts, intents, and source provenance
- `warnings` for throttling, partial provider responses, and direction-specific failures

Researchers can also provide explicit filtering and ranking criteria with `--criteria-file`:

```bash
frontier-discovery expand 10.1145/3442188.3445922 --criteria-file criteria.json
```

For direct CLI review, the same run can be rendered as readable text instead of JSON:

```bash
frontier-discovery expand 10.1145/3442188.3445922 --criteria-file criteria.json --output-format text
```

Artifacts can also be written to disk for downstream tooling:

```bash
frontier-discovery expand 10.1145/3442188.3445922 --criteria-file criteria.json --output-file artifacts/discovery-run.json
```

Example criteria payload:

```json
{
  "include_terms": ["retrieval"],
  "exclude_terms": ["survey"],
  "preferred_terms": ["ranking", "neural"],
  "preferred_authors": ["Ada Lovelace"],
  "preferred_venues": ["NeurIPS"],
  "preferred_fields_of_study": ["Machine Learning"],
  "min_year": 2021,
  "max_year": null,
  "min_citation_count": 10,
  "text_weight": 1.0,
  "citation_weight": 0.35,
  "recency_weight": 0.25
}
```

When criteria are provided, candidate artifacts also include:

- validated `criteria`
- per-candidate `score` objects with component scores and explanation strings
- `warnings` for candidates filtered out by the criteria

## Demo Vertical Slice (NEI-289)

A self-contained demo discovery CLI with an in-repo deterministic provider is also available:

```bash
frontier-research discover \
  --paper paper:attention \
  --concept retrieval \
  --question "Which papers connect retrieval with agent memory?" \
  --forward-depth 1 \
  --reverse-depth 1 \
  --must-match retrieval \
  --max-candidates 5
```

The demo provider runs end to end without external API setup.

## Test

```bash
python -m pytest
```
