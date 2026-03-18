# LEARNING-010: News Page Paper Counter

## Problem
news.html filter bar showed "11 papers published" after Paper 012 was live. Counter was hardcoded and never updated by any agent during publish.

## Root Cause
The counter and the card list were built by two different processes at two different times. update_news_index() in github_publisher.py was automated to insert new article cards at the top of news.html — but it only touched the card list, not the counter. The counter was a static string set once by a human and never wired into the publish pipeline.

This is a state consistency failure: two pieces of data on the same page (card count and counter display) that should always agree, but no code enforced that agreement.

## Fix
Commit: 496cd7b — news.html + github_publisher.py

Immediate: Changed hardcoded "11 papers published" to "12 papers published" in news.html.

Permanent: Added auto-increment logic to update_news_index() in github_publisher.py. After inserting the new card and before committing, the function now:
1. Uses re.search to find the current counter value in the HTML
2. Extracts the number, adds 1
3. Replaces the old counter string with the new one
4. Commits both changes (new card + updated counter) in one operation

Paper 013 and every future paper will auto-update the counter. No human touch needed.

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
