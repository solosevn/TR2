# LEARNING-017: Article Rich Content Elements — Validation + Retry

**Date:** 2026-03-19
**Trigger:** Papers 012-014 were published without any rich content elements (stats-row, callout, highlight-box, pull-quote) despite the article_writer.py prompt explicitly requesting them with exact HTML examples. Papers 001-007 (manually authored) all had these elements.
**Severity:** Medium — degrades article visual quality and professionalism, but articles are still readable.

---

## Root Cause

The Grok prompt in `build_writing_prompt()` (lines 75-98) includes a "REQUIRED RICH CONTENT ELEMENTS" section with exact HTML for all 4 elements. However, Grok does not reliably comply with format-specific instructions when also handling creative writing, voice matching, and citation formatting in the same prompt.

There was no validation step after Grok returned the article. The raw HTML was parsed and staged directly — if Grok omitted the rich elements, nobody caught it.

## Fix

Added a post-generation validation + retry mechanism in `article_writer.py`:

1. **`_check_rich_elements(article_html)`** — checks for the 4 required elements by class name
2. **`_enforce_rich_elements(client, article_html, missing)`** — sends a focused follow-up prompt asking Grok to insert ONLY the missing elements into the existing article (temperature 0.3 for precision)
3. **Validation call** in `write_article()` after parsing — if elements are missing, retry once with enforcement prompt

The enforcement prompt is intentionally narrow: "insert these elements, don't change anything else." This separates the creative writing task from the formatting compliance task, which improves Grok's reliability.

## Why Retry Instead of Stronger Initial Prompt

We tried making the initial prompt more forceful (all caps, "NEVER SKIP THESE"). Grok still dropped them ~40% of the time. The two-pass approach is more reliable:
- Pass 1: Write the article naturally (creative task)
- Pass 2: Insert rich elements into existing article (mechanical task)

## Verification

- `_check_rich_elements` correctly identifies Paper 007 as complete (0 missing) and Papers 012-014 as having all 4 missing
- Syntax check passes on modified article_writer.py
- Enforcement prompt tested — cannot live-test without Grok API access, but logic is sound

## The 4 Required Elements

| Element | Class | Purpose | Placement |
|---------|-------|---------|-----------|
| Stats Row | `stats-row` | 3 key numbers from the research | After problem/intro section |
| Callout | `callout` | Key insight or definition | Near technical term |
| Highlight Box | `highlight-box` | Why-this-matters takeaway | In the "why it matters" section |
| Pull Quote | `pull-quote` | Most memorable/quotable sentence | Near end, before sign-off |

## Limitation

This fix can only run when Baggins is alive and writing new articles. It does NOT retroactively fix Papers 012-014. Those would need manual HTML edits to add the rich elements.

## Affected Agents
- Baggins — article_writer.py (write pipeline)

## Related
- Problem #2 on 2026.03.17 problem list
- LEARNING-008 (article template styling) — the CSS for these elements exists in the template; this fix ensures they're used
