# PRD: Frontier Research

Status: Draft

Date: 2026-04-04

Source: Synthesized from Codex thread `019d56f0-d4b1-75f3-ac98-7e8de198d4e9` plus follow-up product framing

License target: Apache-2.0

Product posture: open source, single-researcher MVP

## 1. Product Summary

Build a researcher-controlled research operating system: a surface where papers, ideas, questions, monitors, and experiments enter a unified queue; agents perform shallow triage; the system expands the citation frontier; and only promising outputs get promoted into durable notes, claims, concepts, and experiments.

The core intellectual primitive is a `Frontier`, but the product also needs first-class `Project` support.

A `Frontier` is a live, evolving subgraph around a research question, idea, or thesis. A `Project` is the administrative and planning surface that groups work, goals, and reusable extraction context. Frontiers can link to multiple Projects, and Projects can contain multiple Frontiers.

This product should replace Obsidian for active note-taking while keeping notes stored as Markdown with Obsidian-style wikilinks and backlinks so users can still open the vault in Obsidian or compatible tools.

This is not an issue tracker for researchers. It is not just an agentic notes app either. It is a research observatory, markdown-native vault, and lab operating surface.

## 2. Positioning

The product should borrow from other tools in specific ways:

- from Obsidian: markdown-native storage, wikilinks, backlinks, and graph-friendly notes
- from Linear: visible runtime, queues, runs, review states, and context orchestration
- from Zotero: canonical paper library and provenance anchor
- from modern markdown editors: native editing, fast linking, and filesystem-backed notes

But the product should not be framed as "Linear + Obsidian." The better framing is:

- a research operating system for literature, claims, notes, and experiments
- an observatory where artifacts are primary and chat is only the operator console
- a markdown-native lab operating system for bounded agentic research loops

## 3. Problem

Researchers are overwhelmed by:

- too many papers and too little attention
- fixed extraction tools that do not match project-specific needs
- disconnected workflows for discovery, triage, synthesis, and experimentation
- poor provenance between claims and supporting evidence
- weak support for forward and backward citation traversal grounded in active research questions
- too many agent outputs that are hard to inspect and easy to distrust
- note-taking tools that are flexible but not research-operational

The real bottleneck is not model capability. It is researcher attention and trust.

## 4. Product Thesis

The initial paper extraction is not the product. It is the scout layer.

Its job is to answer two fast questions:

1. Is this paper worth deeper review?
2. Which claims in my synthesis notes could this paper legitimately support or challenge?

That changes the system shape:

- shallow extraction becomes triage, not note-writing
- citation traversal becomes demand-driven, not full-ingest
- synthesis becomes claim-backed, not prose-first
- experiments become bounded optimization loops, not vague autonomy
- durable memory is built incrementally around active frontiers and projects, not through giant one-shot wiki compilation

The atomic unit of trust is:

- claim
- evidence
- inspectability

## 5. Target Users

Primary user:

- individual researcher, PI, or advanced student who already uses Zotero and wants a daily operating surface for literature triage, synthesis, and experiment planning

Secondary users:

- applied ML researchers tracking fast-moving subfields
- interdisciplinary researchers with custom extraction needs

The first version should optimize for a single researcher, not a collaborative lab workspace or shared multi-user vault.

## 6. Design Principles

1. Researcher in control
The researcher decides what enters the canonical library, what gets promoted, and what experiments run.

2. Scout before depth
Every new paper gets a cheap, schema-aware triage pass before any deeper work.

3. Most papers should die in triage
The system should keep the vault clean by filtering aggressively before promotion.

4. Facts and inferences must stay separate
Extracted facts, synthesized connections, and speculative hypotheses must be visibly different object types.

5. Claim plus evidence plus inspectability
Every load-bearing claim must be reviewable through source snippets, page anchors, figure/table references, or Zotero-linked provenance.

6. Suggestions over autopilot
The system should rank, explain, and propose. It should not silently make important research decisions.

7. Frontier-scoped compilation with project context
The system should compile durable knowledge around active questions while still allowing Projects to organize and apply reusable context.

8. Bounded loops beat vague autonomy
Agentic experiment flows should use explicit evaluation criteria, budgets, and keep-or-discard logic.

9. Primary sources first
Papers, repos, datasets, and benchmarks should outrank commentary in both evidence and monitoring.

10. Uncertainty must be visible
Confidence, support count, counterevidence, freshness, and profile version should be first-class.

11. Markdown is the source of truth for notes
Notes should live on disk as Markdown with Obsidian-style wikilinks and backlinks, with JSON and JSONL sidecars for structured state, provenance, and run history.

## 7. Core Product Decisions

- The top-level planning objects are `Project` and `Frontier`, not `Issue`.
- The primary surface is an observatory for reviewing frontier state, not a ticket board.
- Queue items can be papers, ideas, questions, monitors, repos, datasets, or experiment proposals.
- Initial paper extraction is a shallow scout pass and should produce a `TriageCard`, not a full paper note.
- Citation traversal must support both forward and backward expansion.
- Zotero remains canonical for approved papers.
- Suggested papers should not be auto-added to Zotero by default.
- Deep extraction happens only after promotion or explicit approval.
- The durable notes system should be Markdown-first on disk, with JSON and JSONL sidecars for structure and provenance.
- The app should prefer a native Markdown editor rather than outsourcing note editing to an external tool.
- Extraction profiles are owned per researcher and can be applied per Project.
- Frontiers can link to multiple Projects.
- Experiment execution is local-only in the initial phase.
- The first agent provider is Codex SDK behind a modular provider interface so Anthropic Agents SDK can be added later.
- There is no profile marketplace in v1.
- Frontier inheritance is out of scope for v1.
- Chat is an operator console, not the main interface.
- The main interface is the artifact and its evidence rail.

## 8. Three Graphs

Each frontier brings together three graph layers:

### 8.1 Source Graph

- papers
- repos
- datasets
- citations
- authors
- venues

This is where weighted forward and backward traversal lives.

### 8.2 Claim Graph

- concepts
- findings
- synthesis notes
- contradictions
- supporting evidence

This is where the Markdown-native compounding memory layer is strongest.

### 8.3 Run Graph

- queue items
- agent runs
- monitors
- automations
- experiments
- approvals
- promotions

This is where runtime and orchestration become visible.

The observatory is the projection that lets a human inspect all three graphs together.

## 9. Core Object Model

`Project`

- administrative container for research work
- can link to multiple frontiers
- carries reusable extraction-profile selections, goals, and optional Zotero defaults

`Frontier`

- live subgraph around a question, idea, or thesis
- owns queue, monitors, ranking context, claims, and promoted artifacts
- can link to multiple projects

`QueueItem`

- intake object awaiting action
- types: `Paper`, `Idea`, `Question`, `Repo`, `Dataset`, `MonitorAlert`, `ExperimentProposal`

`TriageCard`

- lightweight scout artifact for a paper or source
- answers whether it matters, what it might support or challenge, and what to inspect next

`ExtractionProfile`

- researcher-owned extraction schema and instructions
- can be applied per project
- includes scout fields, deep fields, evidence rules, and validation logic

`SourceNode`

- canonical source object for a paper, repo, dataset, benchmark, or report

`ZoteroItem`

- canonical paper library object for approved papers
- includes metadata, attachments, and deep links back to Zotero

`CitationEdge`

- forward or backward citation relationship with contextual relevance metadata

`Claim`

- structured assertion that can be marked as `ExtractedFact`, `SupportedInference`, or `OpenHypothesis`
- includes confidence, support count, counterevidence, and freshness

`EvidenceAnchor`

- exact supporting or contradicting evidence
- may point to text snippet, page range, figure, table, repo file, benchmark result, or Zotero location

`ConceptNote`

- durable concept-level note compiled from multiple sources and claims
- stored as Markdown with wikilinks/backlinks support

`SynthesisNote`

- cross-source artifact whose content is organized around claims and evidence, not just prose
- stored as Markdown with sidecar provenance

`Run`

- agent execution with inputs, plan, tools, outputs, evaluation result, and trace

`Artifact`

- output of a run
- examples: triage card, comparison table, observatory view, synthesis note, experiment plan, code scaffold, result report

`Promotion`

- explicit transition from provisional output to durable frontier memory

`ExperimentLoop`

- bounded experiment workflow with mutable surface, evaluation harness, time budget, and keep/discard rule

`Thread`

- conversation attached to a frontier, artifact, run, or note
- scoped to a frontier in v1

`VaultFile`

- Markdown note or JSON/JSONL sidecar persisted to disk
- source of truth for notes and durable structured state

## 10. Canonical Object Chain

The minimum useful buildable chain is:

`Project -> Frontier -> QueueItem -> TriageCard -> Claim -> Run -> Artifact -> Promotion`

Interpretation:

- a project gives administrative context
- a frontier gives research context
- queue items trigger work
- triage cards determine attention allocation
- claims determine what matters
- runs produce inspectable outputs
- artifacts become durable only through promotion

## 11. User Experience Overview

The product should feel like a research observatory with three-pane trust-oriented layout.

Left rail:

- Queue
- Frontiers
- Monitors
- Experiments
- Projects
- Saved Views

Center pane:

- Observatory
- Note
- Compare
- Timeline
- Concept Map
- Run Output

Right rail:

- evidence snippets
- citations and Zotero links
- extraction profile used
- linked projects
- run plan and status
- related claims and notes
- promotion controls

The center pane is where the researcher lives. The right rail is where trust is earned.

Default daily experience:

- open a frontier
- review new triage cards
- inspect the top five suggested next papers and why they matter
- review claim alerts and contradictions
- promote selected papers to deep extraction
- approve, edit, or reject experiment proposals
- promote valuable artifacts into durable frontier memory

## 12. Primary Workflows

### 12.1 Add Paper -> Scout -> Review -> Promote

1. Researcher adds a paper to the queue or a watched Zotero collection.
2. System creates a queue item and runs scout extraction.
3. System produces a triage card that answers:
   - what this paper is about
   - why it might matter to this frontier
   - what claims it appears to support or challenge
   - the 2 to 5 most useful evidence snippets
   - which neighboring papers are worth expanding to next
   - whether it deserves deeper review
4. Researcher chooses:
   - `Promote to deep review`
   - `Keep on frontier`
   - `Dismiss`
5. If promoted, system runs deeper extraction and writes a paper note plus structured claims to the Markdown vault with JSON/JSONL sidecars.

### 12.2 Scout -> Expand Frontier -> Suggest Next Papers

1. After scout extraction, system reads references and citation relationships.
2. System expands both backward and forward through the citation graph.
3. System ranks neighbors using a weighted score blending:
   - direct citation relationship
   - frontier question fit
   - extraction profile fit
   - recency
   - author or venue overlap
   - novelty
   - redundancy penalty
   - prior researcher feedback
4. System returns a short ranked list of the next papers most worth attention, each with a one-line reason.
5. Researcher decides whether to keep as suggestion, add to Zotero, or dismiss.

### 12.3 Synthesis Note -> Claim Backing -> Contradiction Alert

1. Researcher or agent creates a synthesis artifact around a frontier question.
2. The artifact is decomposed into structured claims.
3. Each claim stores support, counterevidence, freshness, and evidence anchors.
4. New scout or deep extraction runs are checked against existing claims.
5. The system flags when a new source may support, weaken, or contradict a frontier claim.

### 12.4 Idea -> Literature Loop -> Experiment Proposal

1. Researcher adds an idea or question to a frontier queue.
2. System performs literature search, scout extraction, and claim synthesis around that idea.
3. System proposes:
   - relevant papers
   - key open questions
   - contradictions or gaps
   - one or more bounded experiments
   - a code scaffold and evaluation plan
4. Researcher approves, edits, or rejects.

### 12.5 Approved Experiment -> Bounded Optimization Loop

1. Researcher approves an experiment plan.
2. System defines:
   - mutable surface
   - fixed evaluation harness
   - budget
   - success metric
   - keep/discard rule
3. System generates or edits code within those bounds.
4. Results are compared against the evaluation target.
5. Only improvements are promoted back into the frontier.

This pattern should guide future experiment execution even if the first release stays focused on local execution.

### 12.6 Monitor -> Alert -> Frontier Refresh

1. Researcher creates a standing monitor for topic, venue, author set, or query.
2. System watches primary-source feeds and search providers.
3. Matches enter the frontier as suggestions, not durable library items.
4. Scout extraction runs automatically.
5. The system only surfaces alerts that materially change frontier coverage, support, or conclusions.

## 13. Functional Requirements

### 13.1 Frontier Management

- Support multiple frontiers per user.
- Allow frontiers to link to multiple projects.
- Give each frontier its own queue, monitors, ranking state, and promoted memory.
- Show frontier health using freshness, open questions, contradiction count, and recent activity.

### 13.2 Project Management

- Support multiple projects per user.
- Allow projects to link to multiple frontiers.
- Let a project apply one or more researcher-owned extraction profiles.
- Store project metadata, goals, and optional Zotero defaults.

### 13.3 Queue And States

- Support queue item types for `Paper`, `Idea`, `Question`, `Repo`, `Dataset`, `MonitorAlert`, and `ExperimentProposal`.
- Show clear states such as `Discovered`, `Triaged`, `Promoted`, `Integrated`, `Proposed`, `Approved`, `Rejected`, and `Completed`.
- Present a unified queue with filters rather than separate hard-coded lanes.
- Allow bulk triage for suggested papers.

### 13.4 Scout Extraction

- Automatically run on newly discovered sources and newly added Zotero papers.
- Be fast and low-cost.
- Produce triage cards, not full notes.
- Capture enough structure for claim support, citation expansion, and ranking.
- Extract references and citation context when available.
- Support evidence snippets plus figure and table references where available.

### 13.5 Deep Extraction

- Run only on promotion or explicit approval.
- Apply the active project's extraction profile selection.
- Support custom fields, custom instructions, and validation rules.
- Store exact evidence anchors, not just paraphrases.

### 13.6 Extraction Profiles

- Let researchers define custom scout and deep fields as researcher-owned profiles.
- Allow projects to apply profiles without duplicating ownership.
- Support instructions such as exact extraction requirements and comparability constraints.
- Version profiles so older artifacts retain their original extraction context.
- Offer templates so setup does not feel like programming.

### 13.7 Claim And Evidence System

- Distinguish extracted facts from inferences and hypotheses.
- Require provenance for load-bearing claims.
- Track support count, counterevidence, confidence, and freshness.
- Allow direct click-through to Zotero or source evidence.

### 13.8 Citation Expansion

- Support forward and backward traversal.
- Rank suggestions using both graph structure and LLM relevance.
- Start with explicit feedback signals such as promotion, dismissal, edits, and approvals.
- Explain why each suggested source matters to this frontier.

### 13.9 Zotero Integration

- Treat Zotero as canonical for approved papers.
- Link claims, notes, and artifacts back to Zotero items.
- Do not auto-add suggested papers by default.
- Preserve a future project-level toggle for auto-add behavior.

### 13.10 Markdown Vault And Editor

- Persist notes as Markdown with Obsidian-style wikilinks and backlinks.
- Persist structured state, provenance, and run history as JSON and JSONL sidecars.
- Keep app edits and filesystem edits synchronized.
- Prefer a native Markdown editor with live backlink-aware navigation.

### 13.11 Observatory And Review UX

- Make artifacts primary and chat secondary.
- Show reviewable evidence rails beside claims and outputs.
- Support approve, edit, reject, defer, and promote actions.
- Prefer structured diffs and field-level review over opaque traces.

### 13.12 Ambient Threads And Frontier Q&A

- Attach threads to artifacts, runs, frontiers, and notes.
- Scope thread retrieval to a frontier in v1.
- Allow grounded answers to be promoted into durable notes.

### 13.13 Incremental Frontier Compilation

- Compile only around active frontier questions.
- Promote durable outputs back into concept notes, synthesis notes, and ranked memory.
- Avoid one giant undifferentiated vault compile by default.

### 13.14 Experiment Planning

- Allow experiment proposals to be generated from ideas, contradictions, or missing evidence.
- Generate code scaffolds plus evaluation plans.
- Preserve lineage from experiment to motivating papers, claims, and prompts.
- Keep execution researcher-gated and local-only in the initial phase.

### 13.15 Monitors And Freshness

- Support standing monitors for topics, authors, venues, and search queries.
- Score new papers against frontier context, not only keywords.
- Surface freshness and "material change" indicators.
- Start with manual intake, watched Zotero collections, arXiv, and Semantic Scholar.

### 13.16 Agent Provider Abstraction

- Support Codex SDK first.
- Isolate agent provider logic behind a modular interface.
- Preserve a clean path to Anthropic Agents SDK later.

## 14. Recommended MVP Scope

This product can sprawl quickly. The MVP should prove the research loop before taking on full experiment orchestration.

In scope for MVP:

- single-researcher workspace
- project and frontier object model
- unified queue with filters
- Zotero integration
- scout extraction and triage cards
- researcher-owned extraction profiles applied per project
- evidence anchors and provenance rail
- markdown vault and native editor
- frontier-scoped threads and grounded Q&A
- forward and backward citation suggestions
- claim-backed notes and synthesis notes
- monitor alerts from manual intake, watched Zotero collections, arXiv, and Semantic Scholar
- experiment proposal generation
- local code scaffold generation and local execution behind explicit approval
- Codex SDK provider integration behind a modular abstraction
- evaluation of open-source markdown-native foundations for reuse

Out of scope for MVP:

- multi-researcher collaboration
- unsupervised or cloud experiment execution
- universal full-vault compilation
- large-scale dataset operations
- heavyweight workflow automation across many external systems
- profile marketplace
- frontier inheritance
- preference-learning ML models

## 15. Success Metrics

Primary metrics:

- median time from intake to triage decision
- percentage of triage cards that lead to a confident keep or dismiss decision
- acceptance rate of frontier-expansion suggestions
- number of synthesis claims backed by evidence anchors
- weekly active users reviewing frontier outputs

Quality metrics:

- field-level approval rate for deep extraction
- usefulness rating for contradiction alerts
- percentage of promoted artifacts later reused in notes or runs
- percentage of experiment proposals approved after review

Trust metrics:

- click-through rate from claim to evidence
- edit rate on extracted claims and fields
- rejection rate by run type
- share of load-bearing claims with provenance

## 16. Risks

### 16.1 Agent Sludge

If the system promotes too many weak outputs, the frontier becomes noisy and the user stops trusting it.

Mitigation:

- keep scout lightweight
- require promotion for durable memory
- optimize for filtering, not maximal output volume

### 16.2 Schema Setup Becomes Work

If frontier configuration feels like software development, researchers will bounce.

Mitigation:

- ship templates
- split scout and deep schemas
- keep advanced controls optional

### 16.3 Experiment Runtime Swallows The Product

Execution environments can dominate the roadmap before the literature loop is solid.

Mitigation:

- keep MVP to experiment proposal plus scaffold
- adopt bounded-loop execution only after frontier review UX is strong

### 16.4 Ranking Feels Magical

If suggestion reasons are weak, users will not trust frontier expansion.

Mitigation:

- show short reasons tied to frontier question and evidence
- expose which claim, citation context, or profile field drove ranking

### 16.5 Facts And Inferences Blur Together

If extracted facts and synthesized connections are not clearly separated, the system will generate false confidence.

Mitigation:

- enforce typed claims
- mark inferences explicitly
- require provenance for any load-bearing statement

## 17. Resolved Decisions

- The MVP is for a single researcher only.
- The project is open source and should target the Apache-2.0 license.
- Notes are stored as Markdown with Obsidian-style wikilinks and backlinks.
- Structured state and provenance are stored as JSON and JSONL sidecars.
- Projects are first-class and Frontiers can link to multiple Projects.
- Extraction profiles are per-researcher and can be applied per Project.
- The queue is unified with filters rather than split into fixed lanes.
- Thread retrieval is frontier-scoped in v1.
- The initial monitor set is manual intake, watched Zotero collections, arXiv, and Semantic Scholar.
- Experiment execution starts local-only.
- Codex SDK is the first provider, behind a modular provider abstraction.
- There is no profile marketplace in v1.
- Frontier inheritance is out of scope for v1.
- Preference-learning models are deferred.

## 18. Open Questions

- Which existing open-source Markdown-native foundation is the best fit to reuse for editing, wikilinks, and backlink navigation?
- What is the thinnest viable local sync/indexing layer between Markdown files, sidecars, and app state?
- What is the first acceptable local execution target for experiments: script runner, notebook runner, or project repo task runner?
- When should a frontier artifact be promoted into broader cross-project memory?

## 19. Recommended Sequencing

Phase 1:

- storage model and file layout
- project and frontier model
- unified queue and triage cards
- Zotero linking
- evidence rail
- provider abstraction with Codex SDK

Phase 2:

- markdown vault and native editor
- extraction profiles
- claim system
- frontier-scoped threads and Q&A

Phase 3:

- forward and backward citation expansion
- monitors and freshness
- idea intake

Phase 4:

- experiment proposals, local scaffolds, and local execution
- richer observatory views
- cross-project memory and reuse

## 20. Product One-Liner

Frontier Research is a researcher-controlled operating system where an automated GA scouts the literature, expands the citation frontier, writes Markdown-native notes backed by evidence, and proposes bounded experiments without taking judgment away from the researcher.
