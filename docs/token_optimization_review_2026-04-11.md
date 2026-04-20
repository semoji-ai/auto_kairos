# Auto Kairos V3 Token Optimization Review

Date: 2026-04-11

Scope:
- `auto_kairos_v3` current main pipeline
- Review focus: token optimization under the constraint that the project is Claude CLI only
- Explicitly excluded: Anthropic API prompt caching migration

## Constraint

Do not propose Anthropic API prompt caching as an immediate fix.
This project is Claude CLI only, so the actionable work should focus on:
- reducing prompt size
- narrowing injected context
- eliminating redundant skill loading
- tightening step-specific prompt composition

## Findings

### 1. Both writing styles are always injected, even though only one is active

Current behavior:
- `draft-writer` and `script-director` load:
  - `shared/writing-style`
  - `shared/writing-style-semoji`
  - `shared/writing-style-iromism`
- This happens regardless of the actual `writing_style` in project config.

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:50`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:106`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/pipeline.json:116`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:4030`

Why this matters:
- This wastes tokens on the inactive channel style.
- It also creates conflicting style instructions.

Measured file sizes:
- `writing-style.md`: about 1.9k chars
- `writing-style-semoji.md`: about 9.8k chars
- `writing-style-iromism.md`: about 4.5k chars

Required change:
- Keep `shared/writing-style`
- Inject exactly one active overlay style:
  - `writing-style-iromism` when `writing_style=iromism`
  - `writing-style-semoji` when `writing_style=semoji`
- Do not inject both at once

## 2. script-director static prompt surface is too large

Current behavior:
- `script-director` pulls all of these into the prompt:
  - `script-director/SKILL.md`
  - `writing-style.md`
  - `writing-style-semoji.md`
  - `writing-style-iromism.md`
  - `motion-presets.md`
  - `remotion-design-system.md`

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:106`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:4041`

Measured combined size:
- manuscript mode baseline static surface: about 42.6k chars
- chapters/consistency surface: about 62.5k chars

Why this matters:
- Even without API caching, this is the main token sink in Stage 2.
- Much of this text is not relevant to every script-director mode.

Required change:
- Split shared skills by mode:
  - `manuscript`:
    - `writing-style`
    - active style overlay only
  - `chapters`:
    - `writing-style`
    - active style overlay only
    - `motion-presets`
    - reduced remotion guidance
  - `consistency`:
    - `writing-style`
    - active style overlay only
    - minimal consistency checklist only
- Do not load full `remotion-design-system.md` in every script-director mode

## 3. remotion-design-system is being loaded as a full document where a narrow subset would be enough

Current behavior:
- `script-director` and `assembly-director` both receive full `remotion-design-system.md`

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:110`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:220`

Measured file size:
- `remotion-design-system.md`: about 13.5k chars

Why this matters:
- Most steps do not need the whole design system.
- They usually need a small subset:
  - scene schema reminders
  - allowed layout names
  - motion vocabulary
  - asset placement rules

Required change:
- Split `remotion-design-system.md` into smaller shared skill files or extractors, for example:
  - `remotion-scene-schema.md`
  - `remotion-layout-catalog.md`
  - `remotion-asset-placement.md`
  - `remotion-animation-rules.md`
- Load only the needed subset per step

## 4. creative_brief is injected too broadly

Current behavior:
- `creative_brief` is appended into the prompt for general agent execution, not only where it is most useful

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:4105`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:2824`

Why this matters:
- `creative_brief` helps `script-director manuscript`
- It is much less valuable for:
  - `data-mapper`
  - `fact-verifier`
  - many Stage 3 tasks

Required change:
- Restrict `creative_brief` injection to:
  - `research-orchestrator`
  - `script-director` manuscript mode
  - optionally `script-director` chapters mode
- Do not inject it into low-value steps by default

## 5. manuscript reference block is too large and overlaps with style skills

Current behavior:
- manuscript mode injects:
  - reference prose from `writing-style-{style}.md`
  - vault similar video snippets
- reference prose section can be up to 8,000 chars

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3922`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3958`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3993`

Why this matters:
- The project already loads the style skill itself.
- This block is useful, but currently too large for every manuscript run.

Required change:
- Reduce manuscript references to:
  - 1 curated style excerpt
  - 1 similar vault snippet
- Total recommendation: keep this block under about 1.5k to 2.5k chars

## 6. Chapter workers still inline very large research context

Current behavior:
- chapter prompt builders inline:
  - `research_digest.json` or `research_report.json` up to 50,000 chars
  - `outline.json` up to 50,000 chars
  - chapter manuscript excerpt

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:1873`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:2000`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:113`

Why this matters:
- `chunked_parallel` loses much of its benefit when each worker receives a huge shared context block
- Parallel chapter workers end up re-paying nearly the same context cost

Required change:
- Build chapter-local compact artifacts before worker execution
- Worker inputs should be:
  - chapter-only manuscript slice
  - chapter-only outline slice
  - chapter-only research digest slice
- Do not pass full outline/full digest into every chapter worker

## 7. single-call path can inline up to 80k per file

Current behavior:
- single-call prompt builder can inline up to 80,000 chars from each input file
- it can also inline `scene_specs.json` up to 80,000 chars

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:2549`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:2557`

Why this matters:
- It is manageable only while the number of such steps stays small
- As soon as more steps use this path, token cost becomes unstable

Required change:
- Cap single-call inline context much more aggressively
- Prefer compact digests or field-level extracts
- Suggested target:
  - per input file excerpt: 8k to 12k max
  - scene_specs extract: only the fields needed by that step

## 8. context_memory has no explicit size budget

Current behavior:
- all prior entries before the current step are appended into the prompt
- no char cap
- no top-N pruning
- no category filtering

Reference:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/context_memory.py:175`

Why this matters:
- On long pipelines and reruns, this grows monotonically
- This is especially costly in review/revise loops

Required change:
- Add a hard budget, for example:
  - recent 3 steps max
  - or total 2,000 to 3,000 chars
- Prefer decisions + key facts only
- Drop verbose summaries once a compact entry exists

## 9. progress_reporting block is too verbose for every call

Current behavior:
- prompt includes long reporting instructions and examples

References:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:2793`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:4179`

Why this matters:
- It adds recurring prompt overhead
- It does not materially improve reasoning after the agent has already learned the format

Required change:
- Reduce to a compact contract:
  - path
  - append-only
  - JSON shape
  - 2 short reporting moments

## Already Good

These parts are already moving in the right direction and should be preserved:

- `research_digest.json` exists and is used before full report fallback
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:882`
- chapter-level parallelization exists
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json:113`
- delta review context exists
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3753`
- previous review reuse exists
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3736`
- creative brief has a 2k cap
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3913`
- manuscript reference block has an 8k cap
  - `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py:3958`

## Recommended Implementation Order

1. Active writing style only
2. Restrict creative_brief injection by role/mode
3. Shrink manuscript reference block
4. Split remotion design system into smaller shared skills
5. Build chapter-local compact context artifacts
6. Add context_memory char budget
7. Reduce single-call inline caps
8. Shorten progress_reporting block

## Bottom Line

The biggest current waste is not a missing algorithm.
It is prompt composition discipline:
- too many inactive skills
- too much globally injected context
- too much large-file inline context in chapter workers

The highest ROI fix is:
- make skill injection conditional
- make chapter context local
- keep reference blocks narrow
