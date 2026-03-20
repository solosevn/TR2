# LEARNING-016: Vault Completeness — shared/USER.md and shared/REASONING-CHECKLIST.md

**Date:** 2026-03-19
**Trigger:** Baggins config.py references `shared/USER.md` and `shared/REASONING-CHECKLIST.md` in VAULT_FILES (lines 58-59). Neither file existed. Context loader returned empty strings, causing Baggins to write articles without David's voice guide and select stories without the reasoning discipline.
**Severity:** High — directly degrades article quality and is a contributing factor to Baggins exit 78.

---

## Root Cause

The `shared/` directory was defined in config.py when the agent was first built, but the files were never created. The context_loader.py silently returns empty strings for missing files (line 65), so Baggins ran without errors but also without the personality and reasoning context that SOUL.md says it should always read.

This means every article from Paper 008 onward was written without:
- David's voice, values, and 5-filter test (USER.md)
- The 5-step reasoning checklist (REASONING-CHECKLIST.md)

## Fix

Created both files in `shared/` at the repo root:

**shared/USER.md** (3,538 chars) — David's voice, values, and decision criteria. Synthesized from documented personality content across 6 files:
- agents/baggins/vault/SOUL.md (voice rules, 5-filter test)
- agents/gollum/vault/SOUL.md (personal background, content preferences)
- agents/kennedy/vault/SOUL.md (character, communication style)
- 2026.03.18.1500-sessmem.md (communication rules)
- agents/baggins/vault/PROCESS.md (writing discipline)
- TR2_Full_Operational_Structure_V5.md (operating philosophy)

**shared/REASONING-CHECKLIST.md** (1,236 chars) — 5-step reasoning discipline. Condensed to fit within the 1000-char truncation window used by story_selector.py (all 5 steps visible).

## Verification

1. Both files exist at paths matching config.py VAULT_FILES
2. USER.md contains all 5 filters from the story selection test
3. REASONING-CHECKLIST.md contains all 5 reasoning steps
4. All 5 steps fit within the 1000-char truncation limit of story_selector.py
5. USER.md truncation at 2500 chars (article_writer.py) ends cleanly

## Prevention

When adding entries to VAULT_FILES in any agent's config:
1. Verify the file exists at the referenced path
2. If the file is loaded into a prompt with a truncation limit, verify the critical content fits within that limit
3. Context loaders should log warnings (not silent empty returns) when files are missing

## Affected Agents
- Baggins — article_writer.py, story_selector.py (both consume these files via context_loader)
- All future agents — shared/ files are organizational context, not agent-specific

## Related
- Problem #12 on 2026.03.17 problem list
- LEARNING-014 (agent architecture) — Baggins exit 78 may be partially caused by downstream failures from missing context
