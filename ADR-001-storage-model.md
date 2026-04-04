# ADR-001: Storage Model

**Status:** Proposed
**Date:** 2026-04-04
**Deciders:** Neill Killgore

## Context

Frontier Research stores research artifacts (paper notes, concept notes, synthesis notes, scout cards, claims, extraction profiles, run traces, threads, and queue state) that need to be:

1. **Human-readable and portable.** Researchers must be able to open the vault in Obsidian, a text editor, or any markdown tool. Lock-in is unacceptable for an Apache 2.0 open source project.
2. **Machine-indexable.** The app needs fast lookups by type, status, Frontier, backlinks, and structured fields. A plain directory of markdown files is not queryable at scale.
3. **Git-friendly.** Researchers may version-control their vault. Binary databases break diffs and merges.
4. **Durable.** The filesystem is the source of truth. If the app's index is deleted, it must be fully reconstructable from the files on disk.

The core tension is between human-readable markdown (for notes, synthesis, portability) and structured data (for queue state, run traces, extracted fields, provenance). We need both, and we need a clear rule for what goes where.

## Decision

**Markdown files for anything a researcher might read or edit. JSON/JSONL sidecar files for structured data, provenance, and operational state. A local SQLite index for fast queries, fully rebuildable from disk.**

### What goes in Markdown

- PaperNotes (`.md`) — deep extraction results, human-readable, with YAML frontmatter for structured fields
- ConceptNotes (`.md`) — emergent concept pages with backlinks
- SynthesisNotes (`.md`) — cross-paper synthesis with `[[wikilinks]]` and inline claim citations
- ExtractionProfiles (`.md` with YAML frontmatter) — schema definition, instructions, readable and editable

Markdown files use Obsidian-compatible `[[wikilinks]]` for backlinks. Frontmatter holds structured metadata (type, status, Frontier, timestamps, Zotero URI). The body is free-form markdown.

### What goes in JSON/JSONL

- ScoutCards (`.json`) — structured triage data, reference lists, relevance scores
- Claims (`.jsonl`) — one claim per line, with provenance (source snippet, page/figure, confidence, profile version, run ID)
- Runs (`.json`) — inputs, outputs, trace, profile version, timestamps, status
- Threads (`.jsonl`) — conversation messages, one per line, with author, timestamp, citations
- Queue state (`.jsonl`) — intake items with status, type, timestamps, Frontier assignment
- CitationEdges (`.jsonl`) — forward/backward citations with context and relevance scores

JSON files are the machine-readable layer. They are not intended for direct human editing, but they are plain text, diffable, and portable.

### What goes in SQLite (index only)

- Full-text search index over markdown content
- Backlink index (which notes link to which)
- Structured field index (query by type, status, Frontier, date range, custom fields)
- Claim-to-source index (which claims reference which papers)

**The SQLite database is ephemeral.** It can be deleted and fully rebuilt from the markdown and JSON files on disk. It is never the source of truth. This is the same model Obsidian uses for its internal index.

## Options Considered

### Option A: Markdown + JSON sidecars + SQLite index (chosen)

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — two file formats, plus an index layer |
| Portability | High — plain text, Obsidian-compatible, git-friendly |
| Query performance | Good — SQLite handles thousands of notes efficiently |
| Durability | High — filesystem is truth, index is rebuildable |
| Team familiarity | High — standard tools, no exotic dependencies |

**Pros:** Portable, human-readable, git-friendly, Obsidian-compatible, no vendor lock-in, rebuildable index.
**Cons:** Two file formats to manage. Need a filesystem watcher to keep index in sync. Slightly more complex than a single database.

### Option B: SQLite as primary store

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low — single data store |
| Portability | Low — binary format, not human-readable, breaks git diffs |
| Query performance | Excellent |
| Durability | Medium — database corruption is a real risk |
| Team familiarity | High |

**Pros:** Simple to implement, fast queries, single source of truth.
**Cons:** Not human-readable. Not Obsidian-compatible. Binary diffs. Vendor lock-in via format. Violates the "open and portable" principle of an Apache 2.0 project.

### Option C: Markdown only (no JSON sidecars)

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Portability | Highest |
| Query performance | Poor — all structured data in YAML frontmatter, hard to query |
| Durability | High |
| Team familiarity | High |

**Pros:** Maximum simplicity and portability. Everything is one format.
**Cons:** YAML frontmatter can't cleanly represent claims with provenance, run traces, or thread messages. Frontmatter bloat makes notes unreadable. Reference lists and citation edges don't belong in markdown.

## Trade-off Analysis

The key trade-off is between simplicity (one format) and fitness-for-purpose (right format for each data type). Markdown is the right format for notes researchers read and edit. JSON is the right format for structured provenance, run traces, and operational state. SQLite is the right format for fast queries.

Trying to force everything into markdown (Option C) means either losing structured data or making frontmatter unreadable. Trying to force everything into SQLite (Option B) means losing portability and Obsidian compatibility.

Option A accepts the complexity of two file formats in exchange for using each format where it's strong.

## Directory Layout

```
frontier-research/
├── .frontier/                      # App config and operational state
│   ├── config.json                 # Workspace-level settings
│   ├── index.sqlite                # Rebuildable query index
│   ├── queue.jsonl                 # Global intake queue state
│   └── runs/                       # Run traces
│       └── {run-id}.json
├── profiles/                       # ExtractionProfiles (per-researcher)
│   ├── ml-benchmarks.md            # Profile as readable markdown + YAML schema
│   └── drug-discovery.md
├── projects/                       # Projects
│   └── {project-slug}/
│       ├── project.json            # Project metadata, linked Frontiers
│       └── ...
├── frontiers/                      # Frontiers (research questions)
│   └── {frontier-slug}/
│       ├── frontier.json           # Frontier metadata, active profile, monitors
│       ├── sources/                # Source-level data
│       │   └── {source-id}/
│       │       ├── scout.json      # ScoutCard
│       │       ├── paper.md        # PaperNote (if deep-extracted)
│       │       ├── claims.jsonl    # Extracted claims with provenance
│       │       └── citations.jsonl # CitationEdges
│       ├── concepts/               # ConceptNotes
│       │   └── {concept-slug}.md
│       ├── synthesis/              # SynthesisNotes
│       │   └── {note-slug}.md
│       ├── experiments/            # Experiment proposals and runs
│       │   └── {experiment-id}/
│       │       ├── proposal.md
│       │       ├── code/           # Generated code
│       │       └── results.json
│       ├── threads/                # Threads on artifacts
│       │   └── {artifact-id}.jsonl
│       └── monitors/               # Standing queries
│           └── {monitor-id}.json
└── README.md
```

### Key conventions

- **Source IDs** are derived from DOI when available, otherwise a content hash.
- **Wikilinks** use the pattern `[[frontiers/{frontier}/{type}/{slug}]]` for cross-Frontier links, or `[[{slug}]]` for within-Frontier links (resolved by the index).
- **Frontmatter** in markdown files always includes: `type`, `id`, `frontier`, `created`, `updated`, `status`.
- **Claims JSONL** format: one JSON object per line with fields: `id`, `text`, `source_id`, `evidence` (snippet, page, figure), `confidence`, `profile_version`, `run_id`, `created`.

## Consequences

- **Easier:** Obsidian can open the vault directly. Git versioning works. Export is trivial (it's already files). Any tool that reads markdown can read the notes.
- **Harder:** Need a filesystem watcher to keep SQLite index in sync. Two formats means two serialization paths. Need clear rules for "what goes in frontmatter vs. sidecar JSON."
- **Revisit:** If the vault grows past ~10K sources, SQLite index rebuild time may matter. Consider incremental rebuild or persistent index at that scale.

## Action Items

1. [ ] Implement the directory layout with seed data for one Frontier
2. [ ] Build the SQLite index builder (scan markdown frontmatter + JSON files, populate index)
3. [ ] Build the filesystem watcher (detect changes, update index incrementally)
4. [ ] Define the YAML frontmatter schema for each markdown type
5. [ ] Define the JSON schema for each sidecar type (ScoutCard, Claims, Runs, Threads, Queue, CitationEdges)
6. [ ] Write a `rebuild-index` CLI command that reconstructs SQLite from disk
