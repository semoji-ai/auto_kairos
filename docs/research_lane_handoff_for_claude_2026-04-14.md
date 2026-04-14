# auto_kairos_v3 Research Lane Handoff

Date: 2026-04-14

This note is for Claude to improve `auto_kairos_v3` by borrowing the stronger persistence and discovery-runtime patterns now present in `/Users/jleavens_macmini/Projects/ResearchAgent`.

## Current Strengths In auto_kairos_v3

- lane-first search policy already exists in [auto_agent/data/skills/shared/search-tools.md](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/shared/search-tools.md:3)
- lane tools already exist for Wikipedia, news RSS, and academic search:
  - [auto_agent/tools/wikipedia_lane.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/tools/wikipedia_lane.py:43)
  - [auto_agent/tools/news_rss_lane.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/tools/news_rss_lane.py:122)
  - [auto_agent/tools/crossref_lane.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/tools/crossref_lane.py:127)
- MCP exposure already exists in [auto_agent/tools/mcp_lane_server.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/tools/mcp_lane_server.py:35)
- source ingest already forces lane tools before broad web search in [auto_agent/modules/source_ingest_module.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/modules/source_ingest_module.py:831)

## Main Weaknesses Compared With researchAgent

### 1. No persisted `research_plan.json` for each session

`auto_kairos_v3` has policy and prompts, but it does not appear to emit a durable per-run lane plan equivalent to:

- [projects/researchAgent/scripts/research_query_planner.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_query_planner.py:52)
- [projects/researchAgent/scripts/research_launcher.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_launcher.py:323)

Claude should add a persisted research plan artifact so the ingest run can be resumed and audited without rereading the whole prompt.

### 2. No persisted discovery bundle

`auto_kairos_v3` uses lane tools directly, but it does not appear to save a reusable discovery layer like:

- `discovered_source_candidates.jsonl`
- `source_note_seeds.jsonl`
- `discovery_packets.json`
- `query_expansions.json`
- `discovery_summary.json`

Reference implementation:

- [projects/researchAgent/scripts/research_discovery.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_discovery.py:114)
- [projects/researchAgent/scripts/research_launcher.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_launcher.py:415)

Claude should add a discovery output directory under the session bundle and persist the lane search outputs before deeper synthesis begins.

### 3. No packetized discovery ranking layer

`auto_kairos_v3` lane tools return raw results, but the stronger runtime pattern is:

- lane packet execution
- relevance scoring
- lane-fit scoring
- ranking threshold by lane
- query expansion rounds

Reference implementation:

- [projects/researchAgent/scripts/research_discovery.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_discovery.py:154)
- [projects/researchAgent/scripts/research_discovery.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_discovery.py:912)

Claude should add a ranking layer between lane search and source note registration, rather than letting every lane result flow through equally.

### 4. Source notes do not appear to preserve discovery metadata

The stronger storage pattern is to keep discovery metadata on every source note and manifest row:

- `source_class`
- `trust_tier`
- `trust_score`
- `domain`
- `tier_reason`
- `publisher_resolved`
- `lane_id`
- `discovery_confidence`
- `discovered_via_query`
- `discovery_stage`
- `relevance_score`
- `relevance_band`
- `ranking_score`

Reference implementation:

- [projects/researchAgent/scripts/research_vault.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_vault.py:624)
- [projects/researchAgent/scripts/research_vault.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_vault.py:1394)

Claude should extend the v3 source persistence schema so every source remains explainable after the run.

### 5. No institutional lane beyond the current three tools

`auto_kairos_v3` currently emphasizes:

- Wikipedia
- News RSS
- Academic

The standalone runtime now adds a `primary_institutional` lane using DuckDuckGo HTML plus trust classification:

- [projects/researchAgent/scripts/research_query_planner.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_query_planner.py:83)
- [projects/researchAgent/scripts/research_discovery.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_discovery.py:373)

Claude should add an institutional lane for official archives, museums, `.gov`, `.mil`, `.museum`, and other primary repositories.

## Recommended Implementation Order

1. Add a research plan builder and persist `research_plan.json` per session.
2. Add a `run-discovery` phase that calls the existing lane tools and writes discovery artifacts.
3. Introduce ranking and query-expansion before source note registration.
4. Extend the source manifest schema with discovery metadata.
5. Add an institutional lane and feed it into the same ranking pipeline.

## Minimal Target Files For Claude

- [auto_agent/modules/source_ingest_module.py](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/modules/source_ingest_module.py:798)
- [auto_agent/data/skills/shared/search-tools.md](/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/shared/search-tools.md:8)
- likely a new planner/discovery module under `auto_agent/modules/` or `auto_agent/tools/`
- any source manifest / vault-writer path used by source ingest

## Reusable Reference Files From researchAgent

- [projects/researchAgent/scripts/research_query_planner.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_query_planner.py:52)
- [projects/researchAgent/scripts/research_discovery.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_discovery.py:46)
- [projects/researchAgent/scripts/research_vault.py](/Users/jleavens_macmini/Projects/ResearchAgent/scripts/research_vault.py:624)
- [projects/researchAgent/references/search-tools.md](/Users/jleavens_macmini/Projects/ResearchAgent/references/search-tools.md:1)

## Important Constraint

Do not remove the current lane MCP interface in `auto_kairos_v3`. The goal is not to replace it with the standalone runtime. The goal is to keep the current lane tools and add durable planning, ranking, and persistence around them.
