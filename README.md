# Frontier Research

Frontier Research is a researcher-controlled operating system for literature discovery, triage, synthesis, and experiment planning.

This repository currently includes the first discovery slice for `NEI-292`: a minimal metadata extraction layer that normalizes abstract-visible paper metadata into a stable JSON shape for both seed papers and discovered candidates.

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
