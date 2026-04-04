# ADR-003: Object Relationships

**Status:** Proposed
**Date:** 2026-04-04
**Deciders:** Neill Killgore

## Context

Frontier Research has a rich object model spanning three interlocking graphs (Source, Claim, Run). The relationships between objects drive navigation, scoping, extraction, and provenance. Several relationships are non-obvious and need explicit decisions:

1. **Frontier ↔ Project.** Both exist. How do they relate?
2. **ExtractionProfile scope.** Profiles are per-researcher, applied per-project. But Frontiers use them. What's the ownership model?
3. **Source sharing.** A paper can be relevant to multiple Frontiers. Where does the Source live on disk?
4. **Claims and provenance.** Claims belong to PaperNotes, but a SynthesisNote in Frontier A may reference a Claim from Frontier B.
5. **Threads.** Threads attach to artifacts. Artifacts live in Frontiers. But a vault-wide question thread doesn't belong to any single artifact.

This ADR locks the relationship model so the directory layout (ADR-001) and application logic have a stable foundation.

## Decision

### 1. Frontier ↔ Project: Many-to-Many, Project is the Container

**A Project is an organizational container.** It groups Frontiers, configures defaults (which Profile to apply, which Zotero collection to watch), and provides a scope for the queue and saved views.

**A Frontier is a research question.** It is the intellectual unit — a living subgraph around a question the researcher is pursuing.

Relationships:
- A **Project** has many **Frontiers**.
- A **Frontier** can belong to multiple **Projects** (e.g., a "Scaling Laws" Frontier is relevant to both "LLM Evaluation" and "Efficient Training" Projects).
- A Frontier always has at least one Project. Orphan Frontiers are not allowed.
- The **queue** (IntakeItems) is scoped to a **Frontier**, not a Project. When viewing a Project, the queue shows the union of its Frontiers' queues.

Implementation:
- `projects/{project-slug}/project.json` contains `frontier_ids: [...]`
- `frontiers/{frontier-slug}/frontier.json` contains `project_ids: [...]`
- Both sides of the relationship are stored for fast lookup without index.

### 2. ExtractionProfile: Per-Researcher, Applied Per-Project, Used Per-Frontier

**Profiles are top-level objects owned by the researcher.** They live in `profiles/` at the workspace root, not inside any Project or Frontier.

**A Project specifies which Profile to use by default.** When a Frontier in that Project runs extraction, it uses the Project's default Profile unless overridden.

**A Frontier can override the Project's Profile.** This handles the case where one Frontier in a Project needs different extraction fields (e.g., a "Methods" Frontier cares about different fields than a "Benchmarks" Frontier, both in the same Project).

Resolution order:
1. Frontier-level Profile override (if set)
2. Project-level default Profile
3. Workspace-level default Profile (if set in config)

Implementation:
- `profiles/{profile-slug}.md` — the Profile definition (YAML frontmatter schema + markdown instructions)
- `profiles/{profile-slug}.versions/` — version history (each version is a snapshot)
- `projects/{project-slug}/project.json` contains `default_profile: "{profile-slug}"`
- `frontiers/{frontier-slug}/frontier.json` contains optional `profile_override: "{profile-slug}"`

### 3. Sources: Shared Across Frontiers, Stored Once

**A Source (paper, preprint, dataset) is stored once in the filesystem**, not duplicated per-Frontier. Sources live under a global `sources/` directory.

**Frontiers reference Sources, they don't contain them.** A Frontier's `frontier.json` contains `source_ids: [...]`. The actual Source data (ScoutCard, PaperNote, Claims, CitationEdges) lives in `sources/{source-id}/`.

This means:
- Adding the same paper to two Frontiers doesn't duplicate it on disk.
- A deep extraction run tags its Claims with the Frontier and Profile that produced them.
- If two Frontiers extract the same paper with different Profiles, both sets of Claims coexist in the Source's `claims.jsonl`, tagged by Frontier ID and Profile version.

Updated directory layout (revising ADR-001):

```
frontier-research/
├── .frontier/                      # App config and operational state
│   ├── config.json
│   ├── index.sqlite
│   └── runs/
│       └── {run-id}.json
├── profiles/                       # ExtractionProfiles (per-researcher)
│   ├── {profile-slug}.md
│   └── {profile-slug}.versions/
├── sources/                        # Sources (global, shared across Frontiers)
│   └── {source-id}/
│       ├── scout.json              # ScoutCard
│       ├── paper.md                # PaperNote (if deep-extracted)
│       ├── claims.jsonl            # Claims (tagged by frontier_id, profile_version)
│       └── citations.jsonl         # CitationEdges
├── projects/
│   └── {project-slug}/
│       └── project.json            # Metadata, frontier_ids, default_profile
├── frontiers/
│   └── {frontier-slug}/
│       ├── frontier.json           # Metadata, source_ids, project_ids, profile_override, monitors
│       ├── concepts/
│       │   └── {concept-slug}.md
│       ├── synthesis/
│       │   └── {note-slug}.md
│       ├── experiments/
│       │   └── {experiment-id}/
│       │       ├── proposal.md
│       │       ├── code/
│       │       └── results.json
│       ├── threads/
│       │   └── {artifact-id}.jsonl
│       └── monitors/
│           └── {monitor-id}.json
└── README.md
```

### 4. Claims: Belong to Sources, Scoped by Frontier

A **Claim** is extracted from a Source. It lives in `sources/{source-id}/claims.jsonl`.

Each Claim record includes:
- `id` — unique identifier
- `frontier_id` — which Frontier's extraction produced this Claim
- `profile_id` — which Profile was used
- `profile_version` — which version of the Profile
- `run_id` — which Run produced it
- `text` — the claim text
- `evidence` — `{ snippet, page, figure, table, section }`
- `confidence` — per-Profile confidence score
- `type` — `source_fact` or `inferred_connection`
- `created` — timestamp

**The `type` field is critical.** A `source_fact` is extracted directly from the paper with exact provenance. An `inferred_connection` is generated by an agent connecting claims across papers. Both are stored, but clearly labeled. This distinction was identified in the PRD as essential for trust.

**Cross-Frontier references.** A SynthesisNote in Frontier A can reference a Claim from Source X, even if Source X was extracted under Frontier B. The SynthesisNote uses a claim reference: `[claim:{source-id}:{claim-id}]`. The app resolves this to the full Claim regardless of which Frontier produced it.

### 5. Threads: Attached to Artifacts, Plus Frontier-Level Threads

A **Thread** is a conversation on an artifact. It lives in `frontiers/{frontier-slug}/threads/{artifact-id}.jsonl`.

The `artifact-id` can be:
- A Source ID (thread on a ScoutCard or PaperNote)
- A Concept slug (thread on a ConceptNote)
- A Synthesis note slug (thread on a SynthesisNote)
- An Experiment ID (thread on an ExperimentProposal)
- The special value `_frontier` — for vault-wide questions scoped to the Frontier

Each message in a Thread:
```json
{
  "id": "msg-uuid",
  "author": "researcher" | "ga",
  "text": "...",
  "citations": [{"claim_id": "...", "source_id": "..."}],
  "spawned_run_id": null | "run-uuid",
  "promoted_to": null | "synthesis/{note-slug}",
  "created": "2026-04-04T12:00:00Z"
}
```

Key behaviors:
- A GA response that spawns a Run records `spawned_run_id` for traceability.
- A GA response that gets promoted to a SynthesisNote records `promoted_to` for provenance (this answer became a durable note).
- Citations in thread messages use the same `[claim:{source-id}:{claim-id}]` format as SynthesisNotes.

### 6. Zotero Integration: Link, Don't Embed

A Source's `scout.json` and `paper.md` frontmatter include a `zotero` field:
```json
{
  "zotero": {
    "item_key": "ABC123",
    "library_id": "12345",
    "uri": "zotero://select/library/items/ABC123",
    "synced_at": "2026-04-04T12:00:00Z"
  }
}
```

This is a link, not an embed. The product never writes to Zotero unless the researcher triggers an explicit "add to Zotero" action. The `synced_at` field tracks when metadata was last read from Zotero.

### 7. Monitors: Scoped to Frontiers

Monitors live in `frontiers/{frontier-slug}/monitors/{monitor-id}.json`:
```json
{
  "id": "monitor-uuid",
  "type": "arxiv" | "semantic_scholar_citations" | "zotero_collection",
  "query": { ... },
  "profile_id": "ml-benchmarks",
  "last_checked": "2026-04-04T12:00:00Z",
  "created": "2026-04-04T10:00:00Z"
}
```

When a Monitor fires, it creates IntakeItems in the Frontier's queue (`.frontier/queue.jsonl`), tagged with `monitor_id` for traceability.

## Options Considered

### Sources: Per-Frontier (rejected) vs. Global (chosen)

**Per-Frontier** (sources inside `frontiers/{slug}/sources/`):
- Simpler scoping: everything for a Frontier is in one directory.
- But: duplicates Sources shared across Frontiers. Wastes disk. Claims diverge without cross-reference.

**Global** (sources in top-level `sources/`):
- No duplication. Claims tagged by Frontier.
- But: slightly more complex cross-reference logic.

Chose global because duplication is worse than indirection, especially for an open vault format.

### Profiles: Per-Project (rejected) vs. Per-Researcher (chosen)

**Per-Project** (profiles inside projects):
- Simpler scoping.
- But: a researcher reuses the same Profile across Projects. Duplication and drift.

**Per-Researcher** (profiles at workspace root):
- Reusable. One Profile, many Projects.
- Applied per-Project (default) with per-Frontier override.

Chose per-researcher because researchers develop Profiles over time and apply them across their work.

## Consequences

- **Easier:** Sources are never duplicated. Profiles are reusable. Frontiers can share Sources naturally. Cross-Frontier claim references work.
- **Harder:** Deleting a Frontier doesn't delete its Sources (they may be referenced elsewhere). Need a "garbage collection" pass for orphaned Sources. Claims file grows with multi-Frontier extractions on the same Source.
- **Revisit:** If multi-researcher collaboration is added, Profile ownership and Source sharing semantics will need rethinking. For now, single-researcher simplifies everything.

## Action Items

1. [ ] Implement the revised directory layout from this ADR (supersedes ADR-001's layout)
2. [ ] Define JSON schemas for: `project.json`, `frontier.json`, `scout.json`, `claims.jsonl` (per-claim), `thread.jsonl` (per-message), `monitor.json`, `queue.jsonl` (per-item)
3. [ ] Define YAML frontmatter schemas for: PaperNote, ConceptNote, SynthesisNote, ExtractionProfile
4. [ ] Implement claim reference resolution: `[claim:{source-id}:{claim-id}]` → full Claim object
5. [ ] Implement Profile resolution: Frontier override → Project default → Workspace default
6. [ ] Implement Source deduplication (DOI-based or content-hash-based)
7. [ ] Document the object model in a `docs/data-model.md` with an ER diagram
