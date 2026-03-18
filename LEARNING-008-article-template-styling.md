# LEARNING-008: Article Template Styling & Rich Content

## Problem
Paper 012 looked visually thin compared to Papers 001-011. Two root causes:
1. Stray closing p tag after every figure - html_stager.py split article_body on closing p, inserted figure HTML, then rejoined. This created orphan closing tags corrupting HTML structure.
2. No rich content elements - article_writer.py Grok prompt only specified p, h2, and strong. Never told Grok to use stats-row, callout, highlight-box, or pull-quote CSS classes.

## Fix
Commit A: 8b2e3fd - html_stager.py - Replaced split/rejoin with re.finditer to locate exact character offset of 2nd closing p tag, insert figure at that position.
Commit B: 7bb5169 - article_writer.py - Added REQUIRED RICH CONTENT ELEMENTS section mandating stats-row, callout, highlight-box, pull-quote with exact HTML templates.

## Pattern: Template-Prompt Contract
When CSS defines visual elements, the content generation prompt MUST reference those elements with exact HTML examples. Otherwise the LLM defaults to basic tags only.

## Prevention Checklist
1. When adding CSS class to template, ALSO add it to article_writer.py prompt
2. Never use string split/rejoin to manipulate HTML - use regex position finding
3. After template changes, diff test article against known-good article
4. Kennedy should review article HTML structure during approval, not just content

## Affected Agents
- Baggins - html_stager.py and article_writer.py
- Kennedy - should add HTML structure review to approval checklist
