# LEARNING-009: Telegram Message Truncation

## Problem
Telegram article preview messages cut text mid-word: "scores well on cre", "timeliness in impro". Made Kennedy look broken to David during the approval flow.

## Root Cause
kennedy.py format_pending_review() used raw Python slicing: reasoning[:300] and runner_up[:150]. Python string slicing has no concept of word boundaries — it cuts at the exact character index regardless of whether it lands in the middle of a word.

## Fix
Commit: 1a774dc — kennedy.py
Replaced both truncations with word-boundary-aware logic:
- Old: {reasoning[:300]}
- New: {(reasoning[:300].rsplit(" ", 1)[0] + "...") if len(reasoning) > 300 else reasoning}

rsplit(" ", 1)[0] finds the last space before the 300-char limit and cuts there. Ellipsis appended only when text was actually truncated.

Same pattern applied to runner_up[:150].

## Pattern: Smart Truncation
Never use raw string slicing for user-visible text. Always break at word boundaries.

Template:
text[:limit].rsplit(" ", 1)[0] + "..." if len(text) > limit else text

## Prevention Checklist
1. Every string slice that appears in a user-facing message MUST use word-boundary truncation
2. Search codebase for [:NNN] patterns in f-strings — each one is a potential mid-word cut
3. Kennedy should treat her Telegram messages as professional communication, not debug output

## Affected Agents
- Kennedy — format_pending_review() in kennedy.py
- Any future agent that sends truncated text to Telegram

## Related
- Problem #3 on 2026.03.17 problem list
