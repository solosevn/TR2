# LEARNING-015: Post-Scoring Model Deduplication

**Date:** 2026-03-19
**Trigger:** Leaderboard showed "Grok Code Fast 1" at #1 and "grok-code-fast-1" at #2 — same model, same scores, listed twice. 179 duplicate groups found across 1,354 models.
**Severity:** High — inflates model count, distorts rankings, undermines data credibility.

---

## Root Cause

Different scrapers return the same model under different names:

- Chatbot Arena / LMSys: `"Grok Code Fast 1"` (display name)
- OpenRouter / API sources: `"grok-code-fast-1"` (API slug)
- Older benchmarks: `"Grok Code Fast"` (no version suffix)

The `canonicalize()` function and ALIASES dict handle SOME known variants, but the ALIASES dict can't keep up with 1,354 models from 37 sources. Names arrive faster than aliases can be manually added.

The `auto_discover_models()` function deduplicates against existing models but NOT against newly discovered models in the same batch. And there was NO dedup pass after scoring.

## Fix

Added a post-scoring dedup pass in `unified_ddp.py` main() — after all models are scored and ranked, before writing JSON:

1. Normalize every model name with `_normalize()` (lowercase, dashes→spaces, collapse whitespace)
2. Group models by normalized key
3. When duplicates exist, keep the entry with the highest today-score
4. Merge `category_count` and `source_count` (take max from group)
5. Re-rank the deduped list
6. Write the clean data

**Result:** 1,354 models → 1,119 after dedup (235 duplicates merged).

## Why Post-Scoring (Not Pre-Scoring)

Deduping before scoring would require matching raw scraped names to canonical models BEFORE we know what scores they map to. The scoring loop already does fuzzy matching via `match_name()`, but it matches scraped names to model entries — it doesn't merge model entries with each other.

Post-scoring is simpler and safer: every model already has its final score. We just collapse entries that normalize to the same string and keep the best one.

## Key Function: `_normalize()`

This is the dedup key function. It:
- Lowercases
- Replaces dashes and underscores with spaces
- Normalizes version separators ("4-5" → "4.5")
- Strips "v" prefix from versions
- Collapses whitespace

So `"Grok Code Fast 1"` and `"grok-code-fast-1"` both become `"grok code fast 1"` → same key → merged.

## Edge Cases

- Models with version suffixes vs. without (e.g., "Grok Code Fast" vs "Grok Code Fast 1") are correctly kept separate — different normalized keys means different models.
- If two variants have different pillar coverage, the one with the higher composite score wins, and we take the max of both coverage counts.

## Prevention

The ALIASES dict should still be maintained for known important models (top 50) to ensure consistent display names. But the post-scoring dedup is the safety net that catches everything ALIASES misses.

## Affected Agents
- Gimli — unified_ddp.py (scoring pipeline)

## Related
- Problem #10 and #11 on 2026.03.17 problem list
- Problem #11 (perfect 100.00 scores) was found to be expected behavior — min-max normalization correctly yields 100.0 for the top model per source
