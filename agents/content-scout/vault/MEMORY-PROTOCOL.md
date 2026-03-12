# GOLLUM MEMORY-PROTOCOL v1.0
## Intelligence Gatherer — Content Scout
> **Agent:** Gollum
> **Role:** Intelligence Gatherer / Content Scout
> **Reports to:** Baggins → Kennedy → Gandalf → David
> **Version:** 1.0 — March 12, 2026

---

## PURPOSE

Gollum scrapes 15+ sources every 30 minutes for 15.5 hours a day. That's ~31 scrape cycles per day, ~217 per week. Without memory, each cycle starts from zero. With memory, each cycle builds on everything Gollum has ever learned about sources, stories, blocking patterns, truth filter effectiveness, and what Baggins actually wants.

This protocol defines how Gollum reads, writes, and queries memory so every cycle is smarter than the last.

---

## MEMORY ARCHITECTURE

```
GOLLUM MEMORY STACK

┌─────────────────────────────────────────────────────┐
│  Layer 1: SOUL.md                                    │
│  Purpose: Identity, mission, principles, rules       │
│  Read: Once per day (at scrape window open)          │
│  Write: Never (David owns this)                      │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 2: CONFIG.md                                  │
│  Purpose: Technical config, model settings, paths    │
│  Read: Once per day (at scrape window open)          │
│  Write: Only when infrastructure changes             │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 3: SOURCES.md                                 │
│  Purpose: Source list, URLs, categories, base weights│
│  Read: Every briefing cycle (5:30 AM)                │
│  Write: When adding/removing sources                 │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 4: TRUTH-FILTER.md                            │
│  Purpose: 4-layer filter methodology, thresholds     │
│  Read: Every scrape cycle                            │
│  Write: When filter rules need updating              │
│  Retention: Permanent                                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 5: STYLE-EVOLUTION.md                         │
│  Purpose: Source weight adjustments, scraping rules   │
│           learned from data                          │
│  Read: Every briefing cycle                          │
│  Write: When source weight change is confirmed       │
│  Retention: Permanent (rules accumulate)             │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 6: LEARNING-LOG.md                            │
│  Purpose: Raw observations — source issues, filter    │
│           performance, scraping anomalies            │
│  Read: Tail every briefing cycle                     │
│  Write: After every scrape cycle with notable events │
│  Retention: Rolling — keep last 60 days              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 7: tried_fixes.jsonl                          │
│  Purpose: What was tried when sources broke, what     │
│           worked, what didn't                        │
│  Read: Before any remediation attempt on a source    │
│  Write: After any attempt to fix a source issue      │
│  Retention: Permanent (append-only)                  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 8: scout-data.json                            │
│  Purpose: Working memory — items seen in last 3 days │
│  Read: Every scrape cycle (dedup check)              │
│  Write: Every scrape cycle (new items appended)      │
│  Retention: 3 days (auto-prune older items)          │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 9: scout-feedback.json                        │
│  Purpose: Baggins' feedback — what got selected      │
│  Read: Every briefing cycle                          │
│  Write: Baggins writes this (Gollum reads only)      │
│  Retention: Rolling                                  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 10: SCOUT-DIRECTIVE.md (future)               │
│  Purpose: Baggins' priority instructions             │
│  Read: Every briefing cycle (when it exists)         │
│  Write: Baggins writes this (Gollum reads only)      │
│  Retention: Updated by Baggins as priorities shift   │
└─────────────────────────────────────────────────────┘
```

---

## READ-BEFORE-ACT PROTOCOL

### Before Each Scrape Cycle:
```
MEMORY QUERY:
1. Check tried_fixes.jsonl → Any sources currently flagged as problematic?
   - If source is flagged as BLOCKING → use adjusted approach or skip
   - If source is flagged as DEGRADED → scrape but note quality
2. Check scout-data.json → What items have I already seen? (dedup)
3. If any source timed out last cycle → increase timeout or add delay
```

### Before Each Briefing (5:30 AM):
```
MEMORY QUERY:
1. Read STYLE-EVOLUTION.md → Current source weight adjustments
2. Read LEARNING-LOG.md tail → Recent source quality observations
3. Read scout-feedback.json → What did Baggins select from my last briefing?
4. Read SCOUT-DIRECTIVE.md (if exists) → What does Baggins want me to prioritize?
5. Apply all learnings to today's ranking and selection
```

### Before Attempting to Fix a Source Issue:
```
MEMORY QUERY:
1. Read tried_fixes.jsonl → Have I tried to fix this source before?
   - Filter by source name
   - If previous fix WORKED → apply same fix
   - If previous fix FAILED → try a DIFFERENT approach
   - If 3 attempts failed → escalate to Baggins
2. Check LEARNING-LOG.md → Any related observations about this source?
3. Compile: what I know, what I've tried, what I recommend
```

### Before Proposing a New Source:
```
MEMORY QUERY:
1. Check SOURCES.md → Is this source already in the list?
2. Check tried_fixes.jsonl → Have I evaluated this source before?
3. Check LEARNING-LOG.md → Any notes about this source type?
4. Evaluate: does this source fill a coverage gap?
5. Propose to Baggins with evidence
```

---

## WRITE-AFTER-OUTCOME PROTOCOL

### After Each Scrape Cycle (if notable events):
```
WRITE TO LEARNING-LOG.md:
- Timestamp
- Sources scraped (count)
- New items found (count)
- Items filtered out (count + top reasons)
- Any source errors or timeouts
- Any new blocking patterns detected
- Any notable items that scored unusually high or low
```

### After Each Briefing Delivery:
```
WRITE TO LEARNING-LOG.md:
- Briefing timestamp
- Stories included (count, top 3 titles)
- Truth scores distribution (high/medium/low)
- Cross-confirmation patterns
- Any SCOUT-DIRECTIVE alignment notes
```

### After Receiving Baggins' Feedback:
```
PROCESS scout-feedback.json:
- Which story was selected?
- From which source?
- What truth score did it have?
- Was it in top 3 or lower?

WRITE TO LEARNING-LOG.md:
- Selection analysis
- Source performance note
- "What I'd change about tomorrow's ranking"

POTENTIALLY WRITE TO STYLE-EVOLUTION.md:
- If source consistently produces selections → boost weight
- If source never produces selections (30+ days) → decrease weight
```

### After Any Source Issue Fix Attempt:
```
WRITE TO tried_fixes.jsonl:
{
  "date": "2026-03-12",
  "source": "techcrunch.com",
  "issue": "HTTP 429 rate limiting after 3rd request",
  "what_tried": "Added 3-second delay between requests",
  "outcome": "SUCCESS — all items scraped without 429",
  "lesson": "TechCrunch needs minimum 3-second spacing",
  "affects": ["scraping", "config"],
  "escalated": false
}
```

---

## MEMORY HYGIENE

### What to Keep Forever:
- tried_fixes.jsonl (append-only, never prune)
- STYLE-EVOLUTION.md rules (accumulate)
- SOURCES.md (master source list)
- TRUTH-FILTER.md (filter methodology)
- RUN-LOG.md (lightweight permanent record)

### What to Prune:
- scout-data.json: items older than 3 days
- LEARNING-LOG.md: entries older than 60 days → archive
- scout-feedback.json: process and archive after incorporating learnings

### Data Integrity:
- Never overwrite existing entries — always append
- Never delete tried_fixes.jsonl entries
- If scout-data.json exceeds 500KB → force prune to last 24 hours
- If conflicting data appears (e.g., source both blocking and working) → log conflict, test manually on next cycle

---

## INSTITUTIONAL KNOWLEDGE GOLLUM BUILDS

Over weeks and months, Gollum's memory becomes a knowledge base about the AI news ecosystem:

| Knowledge Type | Where It Lives | How It's Used |
|---|---|---|
| Which sources break news first | LEARNING-LOG.md | Priority scraping order |
| Which sources get blocked at what rate | tried_fixes.jsonl | Adaptive request spacing |
| What time of day sources publish new content | LEARNING-LOG.md | Optimal scraping schedule |
| What hype keywords are trending | LEARNING-LOG.md + TRUTH-FILTER.md | Filter adjustments |
| What Baggins actually selects | scout-feedback.json → STYLE-EVOLUTION.md | Source weight optimization |
| What story types readers engage with | Via Baggins' SCOUT-DIRECTIVE.md (future) | Priority ranking |

---

## REPORTING CHAIN FOR MEMORY ESCALATION

```
Gollum → Baggins → Kennedy → Gandalf → David

Memory escalation rules:
- Source temporarily slow/flaky → Gollum handles (adjust timing, retry)
- Source blocked or dead for 24+ hours → Escalate to Baggins
- Multiple sources failing simultaneously → Escalate to Baggins immediately
- Truth filter letting bad content through → Escalate to Baggins with examples
- Baggins can't resolve → Kennedy gets it in huddle
- Systemic issue → Gandalf → David
```

---

*Gollum remembers everything — every source that blocked him, every fix that worked, every story Baggins chose. He never scrapes blind. He never repeats a failed approach. He builds intelligence about the AI news landscape that no single human could track manually across 31 cycles a day, 217 cycles a week, across 15+ sources. That's the power of memory-driven autonomy.*
