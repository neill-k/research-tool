# Frontier Research

Initial implementation for the first discovery CLI vertical slice described in Linear issue `NEI-289`.

## What exists

- mixed seed intake from direct papers, concepts, and research questions
- seed resolution that distinguishes direct paper seeds from search-derived seeds
- forward and reverse citation expansion controls
- deterministic filtering and ranking with human-readable reasons
- structured JSON output for later scout, queue, and vault workflows

## Run

```bash
python -m frontier_research discover \
  --paper paper:attention \
  --concept retrieval \
  --question "Which papers connect retrieval with agent memory?" \
  --forward-depth 1 \
  --reverse-depth 1 \
  --must-match retrieval \
  --max-candidates 5
```

You can also use the installed script form:

```bash
frontier-research discover --paper paper:attention --concept retrieval
```

## Notes

- The current provider is an in-repo deterministic demo provider so the slice runs end to end without external API setup.
- The provider surface is intentionally thin so a real search and citation backend can replace it later without changing the CLI contract.

## Test

```bash
python -m unittest discover -s tests -v
```
