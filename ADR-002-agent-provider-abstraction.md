# ADR-002: Agent Provider Abstraction

**Status:** Proposed
**Date:** 2026-04-04
**Deciders:** Neill Killgore

## Context

Frontier Research uses LLM agents for scout extraction, deep extraction, synthesis, citation scoring, experiment design, code scaffolding, and thread responses. The initial implementation will use the **OpenAI Codex SDK** as the agent runtime, but the architecture must support adding **Anthropic Agents SDK** (and potentially others) later.

The key tension is between shipping fast with Codex SDK and building an abstraction that doesn't calcify around one provider's API surface. Over-abstracting early wastes time on an interface we don't yet understand. Under-abstracting means painful rewrites when we add the second provider.

Constraints:

- **Open source, Apache 2.0.** The abstraction must be clean enough that community contributors can add providers.
- **Single researcher, local execution.** No need for multi-tenant provider routing or API key management UX in v1.
- **Runs are the unit of agent work.** Every agent invocation is a Run with inputs, outputs, trace, and Profile. The Run model is defined in ADR-001 and ADR-003.

## Decision

**Start with Codex SDK called through a thin wrapper. Extract the provider interface after building steps 3-6 (scout, promote, deep extract, notes, threads) when we know what the agent runtime actually needs.**

### Phase 1: Thin Wrapper (Steps 1-6)

A single module (`agent/provider.ts` or `agent/provider.py`) that:

1. Accepts a `RunRequest` (task type, inputs, profile, frontier context)
2. Calls Codex SDK directly
3. Returns a `RunResult` (outputs, trace, token usage, status)
4. Writes the Run trace to `{run-id}.json` per ADR-001

The wrapper handles:
- Constructing the system prompt from the ExtractionProfile's instruction layers
- Passing the right context (paper content, vault state, frontier scope)
- Capturing the full trace (tool calls, intermediate steps, token counts)
- Error handling and retry logic

The wrapper does NOT yet:
- Abstract over multiple providers
- Define a formal interface/trait/protocol
- Handle provider-specific tool registration differences

### Phase 2: Extract Interface (Before Step 7 or When Adding Second Provider)

Once we've built scout extraction, deep extraction, synthesis, note generation, and thread responses through the wrapper, we'll know the actual shape of the interface. At that point, extract:

```
interface AgentProvider {
  // Run a structured extraction task
  extract(request: ExtractionRequest): Promise<ExtractionResult>

  // Generate a synthesis or answer from vault context
  synthesize(request: SynthesisRequest): Promise<SynthesisResult>

  // Score relevance of a candidate paper to a Frontier
  scoreRelevance(request: RelevanceRequest): Promise<RelevanceResult>

  // Generate an experiment proposal or code scaffold
  generate(request: GenerationRequest): Promise<GenerationResult>

  // Respond in a thread with vault-grounded citations
  respond(request: ThreadRequest): Promise<ThreadResponse>
}
```

This is illustrative. The actual interface will emerge from the code we write in Phase 1. The key principle is: **don't design the interface before you've used the first provider enough to know where the seam is.**

### Provider-Specific Concerns

Things that differ between Codex SDK and Anthropic Agents SDK:
- Tool registration and calling conventions
- Context window management and token limits
- Structured output / JSON mode APIs
- Streaming behavior
- Rate limiting and retry semantics
- Cost reporting

These differences should be encapsulated inside the provider implementation, not leaked into the Run model or the application logic.

Things that should NOT differ between providers (the Run contract):
- RunRequest/RunResult shape
- Trace format (stored in `.frontier/runs/`)
- Profile version reference
- Evidence extraction format (snippet, page, confidence)
- Error categorization (retryable, fatal, partial)

## Options Considered

### Option A: Thin wrapper now, interface later (chosen)

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low now, medium later |
| Time to first loop | Fast — no abstraction design upfront |
| Risk of wrong abstraction | Low — we learn from real usage first |
| Contributor friendliness | Medium now (one provider), high later (clean interface) |

**Pros:** Ship the first usable loop faster. The abstraction is informed by real code, not speculation. Less throwaway work.
**Cons:** The second provider will require refactoring the wrapper into an interface. Brief period of tight coupling.

### Option B: Design the interface upfront

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — interface design before first usage |
| Time to first loop | Slower — 1-2 weeks on abstraction before any extraction works |
| Risk of wrong abstraction | High — we haven't used either SDK for this use case yet |
| Contributor friendliness | High from day one |

**Pros:** Clean from the start. Contributors can add providers immediately.
**Cons:** We'll guess wrong about the interface shape. Tool registration, context management, and streaming work differently across SDKs in ways we can't predict without building.

### Option C: No abstraction, hardcode Codex SDK

| Dimension | Assessment |
|-----------|------------|
| Complexity | Lowest |
| Time to first loop | Fastest |
| Risk of wrong abstraction | N/A |
| Contributor friendliness | Low — adding a provider means rewriting agent code |

**Pros:** Absolute minimum code.
**Cons:** When Anthropic SDK support is needed, it's a painful rewrite scattered across the codebase. Not acceptable for an open source project that promises modularity.

## Trade-off Analysis

Option B sounds responsible but carries the highest risk of wasted work. The Codex SDK and Anthropic Agents SDK have different enough APIs that an upfront interface will either be too generic (useless) or too specific to one provider (wrong). Option C is too short-sighted for an open source project.

Option A balances speed and quality: we call Codex SDK through a thin wrapper (not scattered across the codebase), so the refactoring surface is small and contained when we extract the interface.

## Consequences

- **Easier:** Ship the first scout → promote loop quickly. Agent code stays in one module, easy to find and modify.
- **Harder:** Adding the second provider will require a refactor pass. Contributors who want to add a provider before Phase 2 will need to work with us on the interface design.
- **Revisit:** After completing step 6 (threads with vault Q&A), evaluate whether the wrapper has stabilized enough to extract the interface. If Anthropic SDK support is requested by the community earlier, accelerate Phase 2.

## Action Items

1. [ ] Create `agent/` module with thin Codex SDK wrapper
2. [ ] Define `RunRequest` and `RunResult` types
3. [ ] Define Run trace JSON schema (per ADR-001: `.frontier/runs/{run-id}.json`)
4. [ ] Implement system prompt construction from ExtractionProfile instruction layers
5. [ ] Implement context assembly (paper content, frontier vault state)
6. [ ] Implement trace capture (tool calls, intermediate steps, token counts)
7. [ ] Add basic error handling and retry logic
8. [ ] Document the "when to extract the interface" criteria in CONTRIBUTING.md
