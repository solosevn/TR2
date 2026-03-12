# LEARNING-003: Source Link Integrity Verification

> **Date:** 2026-03-12
> **Severity:** MEDIUM — dead links destroy credibility with visitors and reviewers
> **Affected Agent:** Treebeard (TRSbench Monitor) / Sauron (TR Site Manager)
> **Detected by:** David (manual request) — should be an automated daily check
> **Resolution time:** N/A (all 37 links verified live on first check)
> **Status:** BASELINE ESTABLISHED — 37/37 PASS

---

## 1. Why This Matters

TR2's methodology page (`methodology.html`) is the credibility backbone of the entire leaderboard. It lists every benchmark source with direct links so visitors, researchers, and journalists can verify the data themselves. If any link goes dead:

- **Visitor trust drops instantly** — a dead source link implies the data might be fabricated or stale
- **Reviewers and journalists will call it out** — they WILL click every link
- **SEO impact** — search engines penalize pages with broken outbound links
- **David's reputation** — TR2 positions itself as "verified cited sources." Dead links make that claim a lie.

**The rule:** Every source link on the methodology page must resolve to a live, relevant page. This must be verified daily.

---

## 2. What We Verified (March 12, 2026 Baseline)

### Method:
Browser-based `fetch()` with `no-cors` mode and 8-second timeout per URL. This confirms the server responds — it does NOT verify page content (a server could return 200 with a "page moved" message).

### Results: 37/37 PASS

| # | URL | Pillar | Status |
|---|-----|--------|--------|
| 1 | crfm.stanford.edu/helm/safety/latest/#/leaderboard | Safe | PASS |
| 2 | crfm.stanford.edu/helm/air-bench/latest/#/leaderboard | Safe | PASS |
| 3 | llm-stats.com/benchmarks/simpleqa | Truth | PASS |
| 4 | kaggle.com/benchmarks/google/facts | Truth | PASS |
| 5 | llm-stats.com/benchmarks/truthfulqa | Truth | PASS |
| 6 | halluhard.com/ | Truth | PASS |
| 7 | huggingface.co/spaces/vectara/leaderboard | Truth | PASS |
| 8 | arcprize.org/leaderboard | Reason | PASS |
| 9 | livebench.ai | Reason | PASS |
| 10 | crfm.stanford.edu/helm/capabilities/latest/#/leaderboard | Reason | PASS |
| 11 | lastexam.ai/ | Reason | PASS |
| 12 | arena.ai/leaderboard | Pref | PASS |
| 13 | arena.ai/leaderboard/text | Pref | PASS |
| 14 | tatsu-lab.github.io/alpaca_eval/ | Pref | PASS |
| 15 | swebench.com/ | Code | PASS |
| 16 | evalplus.github.io/leaderboard.html | Code | PASS |
| 17 | livecodebench.github.io/leaderboard.html | Code | PASS |
| 18 | swe-rebench.com/leaderboard | Code | PASS |
| 19 | bigcode-bench.github.io/ | Code | PASS |
| 20 | tbench.ai/leaderboard/terminal-bench/2.0 | Code | PASS |
| 21 | scale.com/leaderboard/swe_bench_pro_public | Code | PASS |
| 22 | scicode-bench.github.io/leaderboard/ | Code | PASS |
| 23 | arena.ai/leaderboard/code | Code | PASS |
| 24 | hal.cs.princeton.edu/gaia | Agent | PASS |
| 25 | os-world.github.io/ | Agent | PASS |
| 26 | taubench.com/#leaderboard | Agent | PASS |
| 27 | scale.com/leaderboard/mcp_atlas | Agent | PASS |
| 28 | huggingface.co/spaces/galileo-ai/agent-leaderboard | Agent | PASS |
| 29 | openrouter.ai/rankings | Know | PASS |
| 30 | huggingface.co/spaces/TIGER-Lab/MMLU-Pro | Know | PASS |
| 31 | crfm.stanford.edu/helm/mmlu/latest/#/leaderboard | Know | PASS |
| 32 | forecastbench.org/baseline/ | Fcast | PASS |
| 33 | rallies.ai/arena | Fcast | PASS |
| 34 | nof1.ai/leaderboard | Fcast | PASS |
| 35 | financearena.ai/ | Fcast | PASS |
| 36 | artificialanalysis.ai/leaderboards/models | Effic | PASS |
| 37 | pricepertoken.com | Effic | PASS |

### Side finding:
The OLD `index.html` (replaced earlier today — see LEARNING-002) referenced `martian.ai/models`, which is completely dead (domain returns SSL/privacy error, company rebranded to `withmartian.com` and pivoted to interpretability research). This link was NOT on the methodology page and is no longer referenced anywhere in the live site. No action needed.

---

## 3. The Autonomous Check — How Agents Should Do This Daily

### Level 1: Reachability Check (run daily, automated)

```python
# link_check.py — Treebeard or Sauron runs this daily
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

METHODOLOGY_URL = "https://solosevn.github.io/TR2/methodology.html"
TIMEOUT = 10  # seconds per link
EXPECTED_SOURCE_COUNT = 37  # update if sources added/removed

def check_methodology_links():
    """Fetch methodology page, extract all external links, verify each one."""

    # Step 1: Fetch the methodology page itself
    try:
        page = requests.get(METHODOLOGY_URL, timeout=TIMEOUT)
        page.raise_for_status()
    except Exception as e:
        return {"status": "CRITICAL", "error": f"Cannot fetch methodology page: {e}"}

    # Step 2: Extract all external links
    soup = BeautifulSoup(page.text, 'html.parser')
    links = list(set(
        a['href'] for a in soup.find_all('a', href=True)
        if a['href'].startswith('http')
    ))

    # Step 3: Verify count matches expected
    if len(links) != EXPECTED_SOURCE_COUNT:
        # Not necessarily an error — sources may have been added/removed
        count_warning = f"Expected {EXPECTED_SOURCE_COUNT} links, found {len(links)}"
    else:
        count_warning = None

    # Step 4: Check each link
    results = []
    for url in sorted(links):
        try:
            r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
            status = "PASS" if r.status_code < 400 else f"FAIL ({r.status_code})"
        except requests.exceptions.Timeout:
            status = "FAIL (timeout)"
        except requests.exceptions.ConnectionError:
            status = "FAIL (connection error)"
        except Exception as e:
            status = f"FAIL ({str(e)[:50]})"

        results.append({"url": url, "status": status})

    passes = sum(1 for r in results if r["status"] == "PASS")
    fails = [r for r in results if r["status"] != "PASS"]

    return {
        "timestamp": datetime.now().isoformat(),
        "total": len(links),
        "passes": passes,
        "fails": fails,
        "count_warning": count_warning,
        "all_pass": len(fails) == 0
    }

if __name__ == "__main__":
    result = check_methodology_links()
    print(json.dumps(result, indent=2))

    if not result.get("all_pass"):
        print("\n⚠️  DEAD LINKS DETECTED — escalate to Sauron/Treebeard")
        for f in result["fails"]:
            print(f"  FAIL: {f['url']} — {f['status']}")
```

### Level 2: Content Verification (run weekly, requires intelligence)

Reachability is necessary but not sufficient. A URL can return 200 but show:
- "This page has moved"
- A login wall
- "Leaderboard under maintenance"
- Completely different content than expected

For Level 2 verification, the agent should:

1. **Fetch the page content** (not just HEAD request)
2. **Check for expected keywords** — each source should contain model names or benchmark data
3. **Flag "empty" pages** — pages that load but show no leaderboard data (same pattern as LEARNING-002)

```python
# Content keywords each source type should contain
CONTENT_CHECKS = {
    "leaderboard": ["GPT", "Claude", "Gemini", "Llama"],  # at least one model name
    "benchmark": ["score", "accuracy", "performance", "eval"],
    "arena": ["elo", "rating", "vote", "battle"],
}
```

### Level 3: Historical Tracking (enables trend detection)

Store daily results in `memory/link_check_history.jsonl`:

```jsonl
{"date": "2026-03-12", "total": 37, "passes": 37, "fails": []}
{"date": "2026-03-13", "total": 37, "passes": 37, "fails": []}
{"date": "2026-03-14", "total": 37, "passes": 36, "fails": [{"url": "...", "status": "FAIL (timeout)"}]}
```

This lets agents detect patterns:
- "This link has failed 3 days in a row — it's probably dead, not just temporarily down"
- "This link fails every Monday morning — the source does weekly maintenance"
- "Source count changed from 37 to 38 — a new source was added to methodology.html"

---

## 4. Diagnosis Flow — When a Link Fails

```
SYMPTOM: Link check reports FAIL for one or more URLs
  │
  ├── Single link failure
  │   ├── Try again after 5 minutes (transient network issue?)
  │   │   ├── Still fails → Check if domain resolves (DNS)
  │   │   │   ├── DNS fails → Domain is dead or moved
  │   │   │   │   └── ACTION: Search for new URL, update methodology.html
  │   │   │   └── DNS works but HTTP fails → Server is down
  │   │   │       └── ACTION: Wait 24h, check again. If 3+ days → find replacement.
  │   │   └── Works now → Transient. Log it. No action.
  │   │
  │   └── Check if the URL redirects to a different domain
  │       ├── YES → Source rebranded (like martian.ai → withmartian.com)
  │       │   └── ACTION: Update methodology.html with new URL
  │       └── NO → Source is just down temporarily
  │
  ├── Multiple links from same domain fail (e.g., all crfm.stanford.edu)
  │   └── Domain-wide outage. Wait. Don't panic.
  │
  └── Many links fail simultaneously
      └── Likely a network issue on OUR side, not theirs. Check internet connectivity.
```

---

## 5. When to Escalate

| Condition | Action |
|-----------|--------|
| 1 link fails, first occurrence | Log it, retry in 5 min, retry next day |
| 1 link fails 3 consecutive days | Escalate to Treebeard: "Source X appears permanently dead" |
| Domain rebranded/moved | Escalate to Sauron: "Update methodology.html link for X" |
| Source count changed (HTML was edited) | Escalate to Treebeard: "Methodology page was modified — verify new source" |
| 3+ links fail simultaneously | Check own network first. If network is fine → Escalate to Elrond |
| methodology.html itself returns non-200 | CRITICAL — escalate to Sauron immediately |

---

## 6. Pattern — Why Sources Go Dead

Sources die for predictable reasons:

1. **Company rebrand** — domain changes (martian.ai → withmartian.com). Most common.
2. **Project discontinued** — academic project loses funding, page goes offline.
3. **URL restructure** — site redesign moves `/leaderboard` to `/benchmarks/leaderboard`. Returns 404.
4. **Paywall added** — source becomes gated. Still returns 200 but shows a login wall.
5. **Temporary maintenance** — weeknight/weekend deployments take the page down for hours.
6. **Rate limiting** — if we check too aggressively, the source blocks our IP. Use HEAD requests and respect rate limits.

**Prevention:** When adding a new source to methodology.html, also add it to the expected URL list in the link checker. When removing a source, update the expected count.

---

## 7. Cadence & Ownership

| Check | Frequency | Owner | When |
|-------|-----------|-------|------|
| Level 1 (reachability) | Daily | Treebeard | 6:00 AM CST (after Gimli DDP completes) |
| Level 2 (content) | Weekly | Sauron | Sunday 6:00 AM CST |
| Level 3 (trend review) | Weekly | Treebeard | Monday huddle prep |
| Fix dead links | As needed | Sauron | Within 24h of confirmed dead link |

---

## 8. Relevance to TR2 Agents

### For Treebeard (TRSbench Monitor):
Run the Level 1 check daily as part of your post-Gimli verification. The methodology page is part of the TRSbench product — if a source link dies, the benchmark's cited source count is effectively wrong. Add to your daily report: "Source links: 37/37 live" or "Source links: 36/37 — [url] down since [date]."

### For Sauron (TR Site Manager):
You own fixing dead links. When Treebeard reports a dead source, your job is to:
1. Find the replacement URL (search for the source name + "leaderboard" or "benchmark")
2. Update `methodology.html` with the new URL
3. Update `index.html` if the source is also referenced there
4. Commit, push, verify the fix is live
5. Log the change in LEARNING-LOG.md

### For Elrond (TrainingRun COO):
During huddles with Treebeard and Sauron, review the weekly link health trend. If sources are dying faster than they're being replaced, it's a signal that the benchmark landscape is shifting and the pillar structure may need review.

### For Gandalf (CEO):
If a prominent source dies (e.g., arena.ai goes offline permanently), this is a strategic issue — it affects the credibility of the entire scoring methodology. Log to The Red Book and consider whether the pillar weighting needs adjustment.

---

## 9. Files Affected

| File | Role | Notes |
|------|------|-------|
| `methodology.html` | Source of truth for all 37 cited links | Check this page directly — never cache the URL list |
| `index.html` | May reference some of the same sources | Cross-check if a source URL changes |
| `link_check_history.jsonl` (future) | Historical log of daily checks | Create in `memory/` when Treebeard is built |

---

## 10. March 12 Baseline Summary

```
Date:    2026-03-12
Checker: Manual (David + Claude via browser)
Method:  Browser fetch with no-cors, 8s timeout
Result:  37/37 PASS
Fails:   None
Notes:   martian.ai/models was dead but NOT on methodology page
         (was only in old index.html, already replaced per LEARNING-002)
```

This is the baseline. Every future check compares against this. If the number of sources changes, this document should be updated with the new expected count and any added/removed URLs.

---

*This document is training data for TR2 autonomous agents. It should be loaded into Treebeard's and Sauron's memory/ directories and referenced during daily site health checks, methodology page audits, and any "source link broken" diagnosis.*
