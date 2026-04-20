# Auto Kairos V3 Token Optimization Follow-up Review v3

Date: 2026-04-11

This is the third follow-up review after the recent token optimization changes.
Prompt caching is excluded because the runtime is Claude CLI.

## Findings

### P2. The main remaining structural optimization is `skill_refs`

The runtime now supports:
- `skill_limits`
- active writing-style filtering
- chapter-scoped context

But `skill_refs` is still not actually present in the agent config.
That means shared skill optimization is still based on truncation rather than true section-level selective loading.

Relevant files:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

Current state:
- `script-director` uses `skill_limits`
- `assembly-director` uses `skill_limits`
- `skill_refs` is still absent from the config

Recommended next step:
- Add `skill_refs` for `script-director`
- Add `skill_refs` for `assembly-director`
- Use true reference slicing instead of front-truncation where possible

### P3. `script-reviewer` still lacks `skill_limits`

`script-director` and `assembly-director` now have explicit skill limits.
`script-reviewer` still does not.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/agents.json`

Impact:
- Usually moderate
- But if ratchet review loops expand, repeated reviewer prompt cost can accumulate

Recommended next step:
- Add `skill_limits` for reviewer shared skills as well

## What Is Clearly Fixed

1. Active writing-style isolation now works at runtime
- Only the active writing-style skill is kept
- Inactive style skills are filtered out

2. `pipeline.json` no longer carries duplicate semoji/iromism skill declarations in the hot path

3. Chapter workers now prefer chapter-scoped context
- `chapter_facts/chapter_{N}.json`
- outline chapter slice

4. `progress_reporting` was compacted and moved into a shared helper

5. `skill_limits` is live and working
- `script-director`
- `assembly-director`

## Current Verdict

The major token-efficiency problems from the earlier reviews are now mostly resolved.

The remaining work is refinement, not rescue:
- introduce `skill_refs`
- extend `skill_limits` to reviewer

At this point, token optimization is in a good state for normal production use.

## Verification

Regression check run:
- `pytest -q tests/test_agent_runner.py`
- Result: `5 passed`
