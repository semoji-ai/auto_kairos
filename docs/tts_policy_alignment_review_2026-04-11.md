# Auto Kairos V3 TTS Policy Alignment Review

Date: 2026-04-11

This review covers the recent TTS policy alignment changes:
- `shared/korean-tts-rules.md`
- `agents/assembly-director/SKILL.md`

## Current Verdict

The core policy mismatch between the TTS shared skill and the assembly-director skill is resolved.

Both now align on the same operating rule:
- `assembly-director` is responsible for filling `narration_tts`
- `generate_tts.py` uses `narration_tts` as-is when no suspicious pattern is detected
- other agents such as `data-mapper` should not fill `narration_tts`

## Findings

### P1. Core policy docs are aligned

These two files are now consistent:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/shared/korean-tts-rules.md`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/assembly-director/SKILL.md`

This is the main improvement.

### P1. Surrounding docs and legacy paths are still stale

The old ownership model still appears in supporting documentation and legacy prompt/material:

- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/docs/agent-architecture.md`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/docs/data-contracts.md`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/prompts/single-call/tts-preprocess.md`

They still describe:
- a separate `tts-preprocess` module as the producer of `narration_tts`
- `narration_tts` existing only after that module runs

That means the top-level policy is fixed, but the wider documentation layer is still inconsistent.

### P2. Legacy `tts_preprocess` runner path still exists

The runner still contains a `tts_preprocess` single-call path and tool mapping.

Relevant file:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/orchestrator/runner.py`

This does not appear to be the main active path now, but it remains callable.

Impact:
- operational ambiguity
- risk of future policy drift
- someone may accidentally treat the old path as canonical

## Token Optimization Impact

This change is good, but it is mainly a policy/contract cleanup rather than a major token reduction.

Current sizes are modest:
- `korean-tts-rules.md`: about 4.6k chars
- `assembly-director/SKILL.md`: about 17.2k chars

So the value of this change is primarily:
- removing contradictory guidance
- clarifying agent responsibility

## Recommended Next Steps

1. Update the stale docs:
- `agent-architecture.md`
- `data-contracts.md`
- `tts-preprocess.md`

2. Decide what to do with the old runner path:
- keep it as explicit legacy/fallback
- or remove it if no longer intended

## Verification

Regression check run:
- `pytest -q tests/test_agent_runner.py`
- Result: `5 passed`
