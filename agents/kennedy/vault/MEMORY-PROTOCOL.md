# MEMORY-PROTOCOL — Kennedy, Media Director

> **Version:** 1.0 — March 13, 2026

---

## The Rule

**Read before acting. Write after acting.**

V1 agents logged but never read back. That's a filing cabinet, not memory. Kennedy reads her memory files at every boot and before every decision. Memory informs action. Action updates memory. The loop closes.

---

## What to Load at Boot

### Always load (every cycle):

1. **results.tsv** (last 20 entries) — What experiments am I running? What's working?
2. **LEARNING-LOG.md** (full file) — Distilled patterns, proven strategies
3. **health_state.json** — Current state of the media arm
4. **reflection_log.jsonl** (last 10 entries) — Recent reflections, hypotheses in progress

### Load on demand (when relevant):

5. **tried_fixes.jsonl** — Before proposing any strategy change, check: "Have I tried this before?"
6. **error_log.jsonl** — Before any API call, check: "Has this endpoint failed recently?"
7. **huddle_log.jsonl** (last 3 entries) — Before daily huddle, review recent huddle context

---

## Memory File Formats

### results.tsv (Karpathy-style experiment log)

```tsv
commit	metric_value	status	description	platform	content_type	timestamp
abc123	4.2%_ctr	keep	X post: question headline for benchmark data	x	benchmark	2026-03-13T09:00:00
def456	1.1%_ctr	discard	LinkedIn: same content, formal tone	linkedin	benchmark	2026-03-13T09:00:00
```

### tried_fixes.jsonl (append-only)

```json
{"date": "2026-03-13", "action": "posted benchmark to r/LocalLLaMA at 10AM", "outcome": "47 upvotes, 12 comments, 23 site visits", "status": "keep", "lesson": "LocalLLaMA engages with raw data more than r/artificial"}
```

### error_log.jsonl (append-only)

```json
{"date": "2026-03-13", "error": "X API rate limit hit", "context": "tried to read metrics at 15min interval", "resolution": "backed off to 20min", "prevention": "check rate limit headers before next call"}
```

### reflection_log.jsonl (append-only)

```json
{"date": "2026-03-13", "hypothesis": "question headlines get more clicks than statement headlines on X", "action": "posted 3 questions vs 3 statements over 6 days", "outcome": "questions: avg 3.8% CTR, statements: avg 2.1% CTR", "why": "questions create curiosity gap, especially for benchmark data where people want to know the answer", "next_step": "default to question headlines for benchmark content on X, test on Reddit next"}
```

### health_state.json

```json
{
  "last_updated": "2026-03-13T21:00:00",
  "status": "healthy",
  "content_on_schedule": true,
  "engagement_trend": "up",
  "platforms_active": ["x", "reddit", "linkedin", "youtube", "hackernews"],
  "experiments_running": 2,
  "experiments_completed_this_week": 7,
  "top_performing_platform": "reddit",
  "top_performing_content_type": "benchmark_comparison",
  "issues": [],
  "escalations_pending": []
}
```

### huddle_log.jsonl (append-only)

```json
{
  "huddle_date": "2026-03-13",
  "parent": "gandalf",
  "attendees": ["baggins", "oden"],
  "solved_at_this_level": [
    {"agent": "baggins", "issue": "article delayed by 1h", "resolution": "Gollum briefing was late, adjusted timeline"}
  ],
  "escalated_to_me": [],
  "escalated_to_gandalf": [],
  "learnings": ["Benchmark comparison articles drive 3x more Reddit traffic than news analysis"]
}
```

---

## When to Write to Memory

### After every content distribution cycle:
- Append to results.tsv: the experiment details and outcome
- Append to tried_fixes.jsonl: what was done and what happened

### After every measurement cycle:
- Update health_state.json with latest metrics
- Append to reflection_log.jsonl if the measurement reveals a pattern

### After every error:
- Append to error_log.jsonl with full context and resolution

### After every huddle:
- Append to huddle_log.jsonl with structured output

### After every self-improvement experiment:
- Append to results.tsv: code change + metric outcome + keep/discard

### Weekly:
- Distill reflection_log patterns into LEARNING-LOG.md
- After 10 experiments: write mini-paper to The Red Book

---

## Memory Hygiene

- results.tsv is append-only. Never delete entries. History is data.
- LEARNING-LOG.md is curated. Old patterns that are superseded get archived, not deleted.
- health_state.json is overwritten each update (it's current state, not history).
- If results.tsv exceeds 1000 entries: archive older entries to results_archive.tsv, keep last 500 active.
- If reflection_log.jsonl exceeds 500 entries: distill into LEARNING-LOG.md, archive raw entries.

---

## The Key V1 Fix

The difference between V1 and TR2 is this file. V1 agents had logs. TR2 agents have memory. Logs are written and forgotten. Memory is read before every decision and written after every action. If Kennedy's context_loader doesn't load memory at boot, Kennedy is operating blind — and that's a bug, not a feature.
