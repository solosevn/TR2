# LEARNING-006: Morning Intelligence — JSON Key Mismatch Between Agents

## Date
March 17, 2026

## Problem
Kennedy's morning intelligence report showed "0 stories from 0 sources" despite Gollum successfully generating a briefing with 3 stories at 5:31 AM. The Telegram message to David contained no useful intelligence data.

## Root Cause
Kennedy's `morning_intelligence()` function read the wrong JSON keys from Gollum's `scout-briefing.json`:

| What Kennedy read | What Gollum writes | Result |
|---|---|---|
| `briefing["stories"]` | `briefing["top_stories"]` | Empty list, 0 stories |
| `briefing["sources_checked"]` | `briefing["stats"]["sources"]` (dict) | 0 sources |

The briefing file existed and was valid JSON. The keys simply didn't match because the two agents were developed independently without a shared data contract.

## Fix Applied
Three changes in `kennedy.py` `morning_intelligence()`:

1. `briefing.get("stories", [])` changed to `briefing.get("top_stories", [])`
2. `briefing.get("sources_checked", 0)` changed to `len(briefing.get("stats", {}).get("sources", {}))`
3. Story iteration loop also updated from `"stories"` to `"top_stories"`

Commit: `15104f7` — "Fix Kennedy morning_intelligence: match Gollum briefing JSON keys"

## Verification
Code now reads the exact keys that Gollum's `scout.py` writes in its `generate_morning_brief()` function. Verified by reading `scout.py` line-by-line to confirm the briefing JSON structure.

## Learning for Agents
When Agent A reads data produced by Agent B, the data contract (JSON keys, file paths, value types) must be explicitly documented and verified. Silent failures from `.get()` with defaults are dangerous — they return plausible-looking zero values instead of crashing, hiding the real problem.

## Pattern: Agent Data Contracts
When two agents share data via files:
1. Document the exact JSON schema in both agents' vault files
2. Use explicit key validation on read: if expected keys are missing, log a WARNING, don't silently default
3. When one agent's output format changes, grep for all consumers of that file
4. Consider a shared schema definition file that both agents import

## Prevention
- Add a validation step in `morning_intelligence()`: if story_count == 0 but the briefing file exists and is non-empty, log a warning about possible key mismatch
- Create a shared `briefing_schema.py` or document the contract in both agents' vault files
- When updating Gollum's briefing format, search Kennedy's code for all references to briefing keys

## Tags
inter-agent-data, json-keys, morning-intelligence, kennedy, gollum, silent-failure
