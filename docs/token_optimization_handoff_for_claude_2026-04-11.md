# Auto Kairos V3 Token Optimization Handoff

Date: 2026-04-11
Target: Claude working on `auto_kairos_v3`
Constraint: We are Claude CLI-only. Do not propose Anthropic API prompt caching changes.

## Scope

This handoff excludes prompt caching entirely.

Focus only on token optimizations that still matter under the current Claude CLI-only architecture.

## Priority Findings

### 1. Load only the active writing style

Current issue:
- `draft-writer` and `script-director` load both `writing-style-semoji` and `writing-style-iromism` at the same time.
- This is unnecessary token cost and can blur style constraints.

Relevant files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/pipeline.json`

What to change:
- Keep shared `writing-style`.
- Load only the active style skill selected for the current run.
- Do not always inject both `writing-style-semoji` and `writing-style-iromism`.

Expected effect:
- Immediate prompt shrink for `draft-writer` and `script-director`.
- Cleaner style control.

### 2. Scope `creative_brief` to only the steps that need it

Current issue:
- `creative_brief` is broadly injected into agent prompts.
- This is useful for manuscript generation and some high-level planning, but low-value for narrower utility steps.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

What to change:
- Keep `creative_brief` for:
  - `research-orchestrator`
  - `script-director` manuscript generation
  - other genuinely concept-shaping steps if needed
- Remove or heavily shorten it for:
  - `data-mapper`
  - `fact-verifier`
  - `assembly-director`
  - narrow review/repair steps

Expected effect:
- Lower dynamic prompt size across the pipeline.
- Less irrelevant project framing in narrow tool-oriented steps.

### 3. Shrink manuscript reference injection

Current issue:
- Manuscript mode injects a large reference block:
  - style reference excerpt up to about 8k chars
  - plus similar vault snippets
- This helps quality, but the current payload is too large.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

What to change:
- First-pass manuscript generation:
  - include at most 1 curated style excerpt
  - include at most 1 similar vault snippet
- Revision and consistency passes:
  - do not re-inject the full large reference block
  - pass only a compact summary or identifiers

Expected effect:
- Significant reduction in `script-director` prompt size.
- Keeps stylistic grounding without paying the full reference cost every pass.

### 4. Stop inlining huge research and outline blocks into every chapter worker

Current issue:
- Chapter-parallel writer prompts inline large chunks of:
  - `research_digest.json` or `research_report.json`
  - `outline.json`
- The same broad context is repeated across parallel worker prompts.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

What to change:
- Build compact chapter-scoped artifacts before launching chapter workers.
- Each chapter worker should receive only:
  - its chapter objective
  - its local outline slice
  - its chapter-relevant facts
  - its chapter manuscript if revising
- Do not inline 50k-scale global research/outline text into every worker.

Expected effect:
- Large token savings in chapter-parallel mode.
- Better boundedness and less context dilution.

### 5. Put a budget on `context_memory`

Current issue:
- Context memory accumulates prior step summaries, decisions, key facts, and manual notes without a hard budget.
- On long ratchet runs this becomes silent prompt growth.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/context_memory.py`

What to change:
- Keep only recent and high-value memory.
- Suggested policy:
  - recent 3 steps max
  - total memory block capped to about 2000-3000 chars
  - always retain explicit manual notes, but summarize older automated entries

Expected effect:
- Prevents long-run prompt creep.
- Makes iterative runs more stable.

### 6. Compress `progress_reporting` instructions

Current issue:
- Progress reporting guidance is repeated verbosely in many prompts.
- It is execution policy, but the current text is longer than necessary.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

What to change:
- Replace the long repeated block with a compact standard form.
- Keep:
  - when to report
  - how often
  - one example
- Remove long explanatory prose and repeated examples.

Expected effect:
- Smaller prompts with no meaningful loss of behavior.

### 7. Reduce single-call inline file payloads

Current issue:
- Single-call mode can inline very large file contents directly into the user prompt.
- This includes large input files and `scene_specs.json`.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

What to change:
- Prefer compact digests or sliced excerpts.
- For large files:
  - summarize first
  - include only relevant sections
  - avoid 80k-style inline payloads

Expected effect:
- Lower token spikes in one-shot paths.
- Better reliability on larger projects.

### 8. Use scoped skill loading for large shared rule documents

Current issue:
- Large shared docs are loaded wholesale even when only a subset is needed.
- This is especially costly for:
  - `remotion-design-system`
  - `motion-presets`
  - `korean-tts-rules`
  - `image-generation`

Relevant files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`

What to change:
- Use scoped skill loading or references instead of always loading the full shared document.
- If the runtime already supports partial skill loading, start using it in agent config.
- If not, split large rule files into smaller operational sections and load only the needed ones.

Expected effect:
- Lower static prompt size for `script-director` and `assembly-director`.

## Recommended Implementation Order

1. Active writing-style only
2. Scope `creative_brief`
3. Shrink manuscript reference injection
4. Chapter-scoped compact artifacts
5. Cap `context_memory`
6. Compress `progress_reporting`
7. Reduce single-call inline payloads
8. Scoped skill loading

## What Not To Spend Time On

- Do not propose Anthropic API prompt caching.
- Do not design around SDK-only assumptions if the current production path is Claude CLI.
- Do not rewrite the whole orchestrator just for token optimization.

## Goal

The goal is not architectural novelty.

The goal is to cut repeated prompt bulk in the existing Claude CLI path while preserving current behavior and workflow shape.
