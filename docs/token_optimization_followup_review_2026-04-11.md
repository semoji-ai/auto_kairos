# Auto Kairos V3 Token Optimization Follow-up Review

Date: 2026-04-11

This is a follow-up review after the recent token optimization changes.
Prompt caching is explicitly excluded from this review because the runtime is Claude CLI, not Anthropic API SDK prompt caching.

## What Improved

1. `context_memory` is now budgeted.
- Recent 3 steps only.
- Hard cap around 2500 chars.
- File: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/context_memory.py`

2. `creative_brief` injection is narrower.
- It is now skipped for `data-mapper`, `fact-verifier`, and `assembly-director`.
- File: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

3. Manuscript reference injection was reduced.
- Style reference excerpt is capped at 3000 chars.
- Vault similar-example injection is now top 1, capped at 2000 chars.
- File: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

4. Single-call and chapter prompt inline caps were reduced.
- Research digest/report: 20000 chars.
- Outline: 15000 chars.
- File: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

## Remaining Issues

### P1. Active writing style is still not isolated

The biggest remaining waste is that `script-director` steps still load both:
- `shared/writing-style-semoji`
- `shared/writing-style-iromism`

This happens in:
- `manuscript_writing`
- `script_split_and_direct`
- `narrative_consistency`
- `script_review_loop`

File:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/pipeline.json`

Why this matters:
- It wastes tokens every run.
- It mixes style rules that should be mutually exclusive.

Required fix:
- Keep `shared/writing-style` as the base.
- Inject exactly one active style skill based on `project_config.writing_style`.

### P1. Chapter-parallel workers still repeat too much global context

Each chapter worker still receives large shared context:
- `research_digest.json` or `research_report.json` up to 20000 chars
- `outline.json` up to 15000 chars

This is repeated across parallel chapter workers.

File:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Why this matters:
- Parallelism loses some of its token efficiency if every worker re-reads the same global material.

Required fix:
- Build a compact chapter-specific context artifact.
- Give each worker only:
  - its chapter facts
  - its chapter outline slice
  - its chapter manuscript slice
  - only the minimal global constraints needed

### P2. `skill_refs` exists, but is still not actually leveraged in config

The loader supports partial shared-skill loading through `skill_refs`, but current agent config is still effectively loading full shared skill files.

Relevant large shared skills still being loaded whole:
- `remotion-design-system.md`
- `motion-presets.md`
- `korean-tts-rules.md`
- `image-generation.md`

Key files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`

Why this matters:
- The mechanism for selective loading already exists.
- The config is not taking advantage of it.

Required fix:
- Add `skill_refs` to the relevant agent definitions.
- Start with:
  - `script-director`
  - `assembly-director`
- Load only the reference sections actually needed by each mode.

### P3. `progress_reporting` is still duplicated in every prompt

This block is not huge, but it is repeated everywhere and contributes little reasoning value once the convention is established.

File:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Required fix:
- Reduce to a one-line instruction plus the file path.

## Recommended Next Order

1. Active `writing_style` only
2. Chapter-specific compact context for parallel workers
3. Roll out `skill_refs` in agent config
4. Compress `progress_reporting`

## Verification Note

Minimal regression check run:
- `pytest -q tests/test_agent_runner.py`
- Result: `5 passed`

This confirms the basic runner path still works, but it does not prove token efficiency by itself.
