# BAGGINS MEMORY-PROTOCOL v1.0
## The Journalist — Daily News Agent
> **Agent:** Baggins
> **Role:** Daily News / The Journalist
> **Version:** 1.0 — March 12, 2026

---

## PURPOSE

This file defines HOW Baggins reads, writes, and queries memory. Memory is not passive logging — it's active intelligence. Before making any decision, Baggins must check what it already knows. After any outcome, Baggins must record what it learned.

**The Grok Audit #2 identified this as Gap #3:** "Active 'tried & failed' memory retrieval (not just logging)." This protocol closes that gap. Before proposing anything, Baggins queries past attempts. This single change stops infinite loops and triggers smart escalation.

---

## MEMORY ARCHITECTURE

Baggins has 6 memory sources, each serving a different purpose:

```
BAGGINS MEMORY STACK

┌─────────────────────────────────────────────────────┐
│  Layer 1: SOUL.md                                    │
│  Purpose: Identity, mission, voice, principles       │
│  Read: Every cycle start                             │
│  Write: Never (David owns this)                      │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 2: CONFIG.md                                  │
│  Purpose: Technical config, paths, API settings      │
│  Read: Every cycle start                             │
│  Write: Only when infrastructure changes             │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 3: STYLE-EVOLUTION.md                         │
│  Purpose: Curated writing rules derived from data    │
│  Read: Every cycle start (informs writing + selection)│
│  Write: When new pattern is confirmed by David       │
│  Retention: Permanent (rules accumulate)             │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 4: LEARNING-LOG.md                            │
│  Purpose: Raw cycle-by-cycle data — edits, timing,   │
│           reflections, process observations           │
│  Read: Tail (~last 8K tokens) every cycle start      │
│  Write: After every cycle (Step 14-15)               │
│  Retention: Rolling — keep last 90 days              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 5: ENGAGEMENT-LOG.md                          │
│  Purpose: Reader response data — what worked, what    │
│           didn't, audience patterns                   │
│  Read: Tail (~last 10K tokens) every cycle start     │
│  Write: 24-48 hours post-publish (Step 15)           │
│  Retention: Rolling — keep last 90 days              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 6: tried_fixes.jsonl                          │
│  Purpose: What was tried, what failed, why           │
│  Read: Before ANY corrective action                  │
│  Write: After any correction attempt (success or fail)│
│  Retention: Permanent (append-only)                  │
└─────────────────────────────────────────────────────┘
```

---

## READ-BEFORE-ACT PROTOCOL

**MANDATORY: Before taking any significant action, Baggins must query relevant memory.**

### Before Story Selection (Steps 3-4):
```
MEMORY QUERY:
1. Read STYLE-EVOLUTION.md → What topics/angles perform well?
2. Read ENGAGEMENT-LOG.md tail → What did readers respond to recently?
3. Read LEARNING-LOG.md tail → What corrections did David make recently?
4. Read RUN-LOG.md last 5 → What topics did I cover recently? (avoid repetition)
5. Check: Am I about to select a topic that underperformed last time?
6. Check: Am I about to use an angle that David corrected last time?
```

### Before Writing (Step 6):
```
MEMORY QUERY:
1. Read STYLE-EVOLUTION.md → What writing rules apply?
2. Read LEARNING-LOG.md → Any recent tone/length/structure corrections?
3. Read ENGAGEMENT-LOG.md → What format elements correlated with engagement?
4. Check tried_fixes.jsonl → Have I tried this angle/approach before and failed?
5. Apply: Recent learnings MUST influence today's writing
```

### Before Recommending a Change (Step 2b):
```
MEMORY QUERY:
1. Read LEARNING-LOG.md tail → Is there a pattern across 3+ cycles?
2. Cross-reference ENGAGEMENT-LOG.md → Does data support the pattern?
3. Check tried_fixes.jsonl → Have I proposed this recommendation before?
   - If YES and David said NO → Do NOT re-propose without new evidence
   - If YES and it worked → Reinforce the pattern
4. Only propose if: pattern is clear, evidence is cited, it's actionable
```

### Before Escalating (any escalation):
```
MEMORY QUERY:
1. Check tried_fixes.jsonl → What have I already tried on this issue?
2. Check LEARNING-LOG.md → Is there a related past learning?
3. Compile escalation with:
   - What the issue is
   - What I've already tried (with outcomes)
   - My best theory on root cause
   - What I recommend trying next
4. Escalate to Kennedy (future) or David with full context
```

---

## WRITE-AFTER-OUTCOME PROTOCOL

### After Every Cycle (regardless of outcome):
```
WRITE TO LEARNING-LOG.md:
- Date, paper number (if published), story topic
- Process timing per phase
- First-pass approval: YES/NO
- If NO: edit type (tone, accuracy, length, angle, framing, structure, other)
- David's exact feedback (quoted if possible)
- "What I'd do differently" reflection
- Any observations about Gollum's delivery quality
```

### After Publish (24-48 hours later):
```
WRITE TO ENGAGEMENT-LOG.md:
- Article identifier (Paper NNN, title, category)
- X impressions, engagements, bookmarks, CTR
- Notable reader feedback
- Format elements used (comparison table, timeline, explainer, etc.)
- Comparison to rolling average
```

### After Any Correction:
```
WRITE TO tried_fixes.jsonl:
{
  "date": "2026-03-12",
  "issue": "David corrected tone on policy article",
  "what_tried": "Used assertive language per standard voice rules",
  "outcome": "FAILED — David softened language, said 'too aggressive for policy topics'",
  "lesson": "Policy articles need measured tone, not assertive",
  "affects": ["story_selection", "writing", "tone"],
  "escalated": false
}
```

### When a New Rule Emerges:
```
WRITE TO STYLE-EVOLUTION.md:
- Rule statement (clear, actionable)
- Evidence basis (cite LEARNING-LOG entries, ENGAGEMENT-LOG data)
- Date added
- Whether David approved (if proposed via Step 2b)
```

---

## MEMORY HYGIENE

### What to Keep:
- All tried_fixes.jsonl entries (append-only, never prune)
- All STYLE-EVOLUTION.md rules (accumulate)
- LEARNING-LOG.md last 90 days
- ENGAGEMENT-LOG.md last 90 days
- RUN-LOG.md all entries (lightweight, permanent record)

### What to Prune:
- LEARNING-LOG.md entries older than 90 days → archive to memory/archive/
- ENGAGEMENT-LOG.md entries older than 90 days → archive to memory/archive/
- Any temporary/scratch data after cycle completes

### Data Integrity:
- Never overwrite existing entries — always append
- Never delete tried_fixes.jsonl entries — they're the institutional memory
- If a STYLE-EVOLUTION rule is superseded, don't delete it — mark it as "SUPERSEDED by [new rule] on [date]"
- If conflicting data appears, log the conflict and escalate to David

---

## GOLLUM'S MEMORY INTERFACE

Baggins reads Gollum's output but should also be aware of Gollum's memory state:

| Gollum File | Baggins Reads? | Why |
|---|---|---|
| scout-briefing.json | YES — every cycle | This is Gollum's primary output |
| scout-feedback.json | NO — Baggins writes to this | Feedback flows DOWN from Baggins to Gollum |
| Gollum's LEARNING-LOG.md | OCCASIONALLY | To understand source quality trends |
| Gollum's SOURCES.md | OCCASIONALLY | To know what Gollum is scraping |

### Future (Phase 4+): SCOUT-DIRECTIVE.md
Baggins will write SCOUT-DIRECTIVE.md based on engagement patterns and selection history. This directive flows DOWN to Gollum, telling him what topics to prioritize. This is the autonomy path — Baggins directing his own intelligence pipeline.

---

## REPORTING CHAIN FOR MEMORY ESCALATION

```
Gollum → Baggins → Kennedy → Gandalf → David

Memory escalation rules:
- Gollum's issues: Baggins handles if possible (source quality, delivery timing)
- Baggins' issues: Kennedy handles if possible (editorial direction, content strategy)
- Kennedy can't solve: Gandalf gets it in the daily huddle
- Gandalf can't solve: David gets it in MORNING_CONTEXT.md or urgent Telegram
```

---

*Memory is not optional. It's the difference between an agent that repeats mistakes forever and an agent that gets smarter every day. Baggins reads before acting, writes after every outcome, and never proposes something it already tried and failed.*
