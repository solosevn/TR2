# LEARNING-010: News Page Paper Counter

## Problem
news.html filter bar showed "11 papers published" after Paper 012 was live. Counter was hardcoded and never updated by any agent during publish.

## Root Cause (Original — 2026-03-17)
The counter and the card list were built by two different processes at two different times. update_news_index() in github_publisher.py was automated to insert new article cards at the top of news.html — but it only touched the card list, not the counter. The counter was a static string set once by a human and never wired into the publish pipeline.

## Fix Attempt #1 (Commit 496cd7b)
Added auto-increment logic using `re.search()` to find and bump the counter. Changed 11 → 12 in news.html.

**This fix was incomplete.** The `re` module was never imported in `github_publisher.py`. The `re.search()` call on line 154 raised a silent `NameError` every time, swallowed by the try/except in `publish_article()`. Papers 013 and 014 both published with cards inserted but counter stuck at 12.

## Root Cause (Real — 2026-03-19)
Missing `import re` in `github_publisher.py`. The auto-increment code existed but could never execute.

**Lesson:** When you add code that uses a module, verify the import exists. When a fix is committed, verify it actually works on the next execution — don't assume.

## Fix #2 (2026-03-19)
1. Added `import re` to `github_publisher.py` (line 9)
2. Corrected news.html counter: 12 → 14 (matching actual paper count)
3. Tested: regex simulation confirms 14 → 15 on next publish

## Pattern: Page State Consistency

When you modify a page by adding content (a card, a row, an entry), check the ENTIRE page for any other element that references a total, count, or summary of that content. Update all of them in the same commit.

One page, one commit, all state consistent.

Questions to ask before committing any page update:
1. Is there a counter or total anywhere on this page?
2. Is there a "last updated" date?
3. Is there a navigation element that references item count?
4. Are there any hardcoded numbers that should be dynamic?

If the answer to any of these is yes, update them in the same operation.

## Prevention Checklist
1. Every function that adds content to a page MUST also update any counters/summaries on that page
2. Never hardcode counts that can be computed — if you must display a number, derive it from the actual content
3. When reviewing a publish commit, verify the counter matches the actual card count
4. Consider replacing hardcoded counters with JavaScript that counts DOM elements on page load

## Affected Agents
- Baggins — github_publisher.py (publish pipeline)
- Kennedy — should verify counter accuracy during approval review

## Related
- Problem #4 on 2026.03.17 problem list
