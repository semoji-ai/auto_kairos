# Auto Kairos V3 Token Optimization Follow-up Review v2

Date: 2026-04-11

This is the second follow-up review after the recent token optimization work.
Prompt caching is excluded because the runtime is Claude CLI.

## Findings

### P2. Shared skill trimming is still only partially applied

`skill_limits` has been added, which is a real improvement, but it is still only applied to `remotion-design-system`.
`skill_refs` is still not present in the agent config, so other large shared skills are still loaded in full.

Relevant files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Remaining large shared skills still loaded whole include:
- `motion-presets.md`
- `image-generation.md`
- `korean-tts-rules.md`
- `image-prompt-rules.md`

Recommended next step:
- Extend `skill_limits` beyond `remotion-design-system`
- Or add real `skill_refs` to `script-director` and `assembly-director`

### P3. `pipeline.json` notes are now stale relative to runtime behavior

The manuscript step note still says the runner injects `writing-style-iromism` reference prose, but the runtime now correctly uses the active `writing_style`.

Relevant files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/pipeline.json`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Impact:
- Not a token-cost bug
- But it creates config/documentation drift and future maintenance confusion

Recommended next step:
- Update pipeline notes to describe active-style injection, not hardcoded iromism wording

### P3. `progress_reporting` is still duplicated across prompt builders

This block has been shortened, which is good, but it is still repeated across prompt construction paths.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Recommended next step:
- Move to a shared compact template or one-line standard block

## What Is Now Clearly Fixed

1. Active writing style isolation is now working at runtime
- Only the active writing style skill is kept
- Inactive style skills are filtered out

2. Chapter worker context is now chapter-scoped first
- `chapter_facts/chapter_{N}.json` is used first
- Outline chapter slice is used first
- This is much better than repeating the full global research/outline block for every worker

3. `skill_limits` is live
- `remotion-design-system` is now truncated by config limit
- This is a real runtime optimization, not just a plan

## Verification

Regression check run:
- `pytest -q tests/test_agent_runner.py`
- Result: `5 passed`

## Current Verdict

The major token-efficiency issues from the previous review are mostly resolved.

What remains is not a blocker:
- partial skill trimming
- config/notes cleanup
- further shared prompt deduplication

The next highest-value change is to expand `skill_limits` or introduce `skill_refs` for the remaining large shared skills.
