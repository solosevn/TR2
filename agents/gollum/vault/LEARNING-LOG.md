# Content Scout — LEARNING-LOG.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Purpose

Raw learning data. Every morning briefing result and every feedback event from the Daily News Agent gets logged here. This is the unprocessed data that feeds STYLE-EVOLUTION.md (curated rules).

---

## Section 1: Briefing Results

Appended by `scout_learning_logger.log_briefing_result()` after each morning brief.

```
### Brief [YYYY-MM-DD]
- **Top 10 stories surfaced:**
  1. [title] | Source: [source] | Truth Score: [score] | AI Verdict: [verdict] | Category: [category]
  2. ...
- **Truth score range:** [min]-[max]
- **Categories represented:** [list]
- **Sources represented:** [list]
- **Items dropped by AI verification:** [count]
- **Ollama status:** [available/unavailable]
- **xAI status:** [available/unavailable]
```

---

## Section 2: Daily News Agent Feedback

Appended by `scout_learning_logger.log_selection_feedback()` when feedback is received.

```
### Feedback [YYYY-MM-DD] — Paper [NNN]
- **Selected story:** [title]
- **Selected source:** [source]
- **Selected truth score:** [score]
- **Selected category:** [category]
- **Rejected candidates:** [count]
- **Top 3 rejected:**
  1. [title] | Source: [source] | Score: [score]
  2. ...
  3. ...
- **Selection pattern:** [Was it the #1 ranked story? If not, what rank was it?]
```

---

## Section 3: Source Performance Tracking

Updated by `scout_learning_logger.update_source_weights()` after each feedback event.

```
### Source Stats [YYYY-MM-DD]
| Source | Stories Surfaced (30d) | Stories Selected (30d) | Selection Rate | Current Weight |
|--------|----------------------|----------------------|----------------|----------------|
| arXiv | [count] | [count] | [%] | [weight]x |
| Hugging Face | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
```

---

## Log Entries

*Entries will be appended below this line by scout_learning_logger.py*

---

## INSTITUTIONAL LEARNING INTAKE — March 12, 2026
### Source: 12 CEO-LEARNING + LEARNING documents from V1 operations (trainingrun-site)
### Ingested by: David Solomon directive — "feed these into Gollum so he learns from them"

The following lessons are distilled from 12 operational learning documents produced during the V1→TR2 migration (March 5-12, 2026). These represent hard-won institutional knowledge from real production incidents. Gollum must internalize these before they are needed — not after.

---

### LESSON G-001: Silent Failures Are the Most Dangerous (from CEO-LEARNING-002, CEO-LEARNING-003)
**What happened:** DDP scrapers failed silently when cron couldn't find the script — zero output, no error, no notification. Data was also silently lost by git `-X theirs` rebase with no error message.
**Rule for Gollum:** Every scrape failure must produce a visible signal. If a source times out, returns 403, or produces zero items — log it and include it in the next Telegram summary. If the entire scrape cycle fails, send an error notification immediately. Never let a failure pass silently. The absence of data IS the alert.
**Applies to:** Every scrape cycle in LOOP.md Phase 1

### LESSON G-002: Restructures Break More Than You Think (from CEO-LEARNING-002, CEO-LEARNING-009)
**What happened:** V10 restructure moved files but didn't update crontab entries, launchd plists, internal paths, or hardcoded data paths. Running agents masked broken configs until the next reboot.
**Rule for Gollum:** After ANY repo restructure or path change: verify REPO_PATH in scout.py, verify scout_context_loader.py paths, verify scout_learning_logger.py paths, verify launchd plist (if one exists), verify vault file GitHub paths in CONFIG.md. Do a test scrape. Don't assume anything works just because it was working before.
**Applies to:** Any migration event (like the TR2 migration we just completed)

### LESSON G-003: Git Rebase -X theirs Is a Data Loss Footgun (from CEO-LEARNING-003)
**What happened:** 5 DDP scrapers each pushed status.json with `-X theirs` rebase strategy. Each push silently discarded the previous scraper's data. Only the last 2 scrapers' data survived.
**Rule for Gollum:** Never use `-X theirs` when pushing files that other agents also write to. If Gollum pushes scout-briefing.json or scout-data.json, use `git pull --rebase` without `-X theirs`. If there's a conflict, resolve it by merging, not by blindly taking the remote version. Better yet: let the coordinator (Baggins or daily_runner) handle shared file pushes.
**Applies to:** scout.py git push operations

### LESSON G-004: Bandaid Fixes Create Debt (from CEO-LEARNING-002)
**What happened:** Stale data files were copied back to repo root to make the site "look right" without fixing the scraper pipeline that generates them. Site appeared alive but served frozen data.
**Rule for Gollum:** If a source stops producing items, don't serve stale cached data as if it's fresh. Flag the source as DEGRADED in LEARNING-LOG.md. If scout-data.json stops being updated, that's a system failure — don't mask it by serving old data. Truth over speed.
**Applies to:** LOOP.md Phase 3 (delivery) and source health monitoring

### LESSON G-005: Verify Code Is Actually Pushed (from CEO-LEARNING-007)
**What happened:** 9 files existed only on David's local Mac and were never committed or pushed. Agent work was done but invisible to production.
**Rule for Gollum:** After writing scout-briefing.json and pushing to GitHub, verify the push succeeded. Check that `git push` returns 0. If it fails, retry once, then log the failure and notify via Telegram. scout-data.json (local working memory) doesn't need to be pushed, but scout-briefing.json (Baggins' input) MUST reach GitHub.
**Applies to:** scout.py git push operations

### LESSON G-006: Be an Employee, Not a Reporter (from CEO-LEARNING-006)
**What happened:** TRSitekeeper ran 24 audit checks, reported pass/fail, went to sleep. Caught zero real problems during the V10 restructure because it only reported — it didn't investigate or fix.
**Rule for Gollum:** Don't just scrape and deliver — learn from what you find. When a source degrades, investigate (check tried_fixes.jsonl, try alternative approaches). When Baggins never selects stories from a source, adjust weights. When the truth filter lets bad items through, tighten it. The difference between L1 and L2 is: L1 scrapes, L2 scrapes AND adapts.
**Applies to:** LOOP.md Phases 4-6 (measure, keep/discard, reflect)

### LESSON G-007: Running Agents Mask Broken Configs (from CEO-LEARNING-009)
**What happened:** Content Scout and TRSitekeeper plists pointed to old pre-V10 paths. The agents kept running from before the restructure, but the next Mac reboot would have silently killed them.
**Rule for Gollum:** If Gollum is started manually (no launchd plist yet), be aware that a Mac reboot means Gollum stops until someone manually restarts. When a launchd plist is eventually created, verify paths match the current TR2 structure. After any path change, `launchctl unload` then `launchctl load` to verify the plist works.
**Applies to:** Operational awareness — Gollum currently has no auto-restart mechanism

### LESSON G-008: Security — .env Files Never in Repo (from CEO-LEARNING-005)
**Rule for Gollum:** Never commit .env files. XAI_API_KEY, TELEGRAM_TOKEN, and TELEGRAM_CHAT_ID all come from environment variables. If you see a credential in any file during scraping or logging, do not include it in scout-briefing.json or any committed file. The repo is public.
**Applies to:** All operations — permanent rule

### LESSON G-009: The Handoff Document Is Institutional Memory (from CEO-LEARNING-008)
**What happened:** MORNING_CONTEXT.md went stale across 4+ sessions. New sessions wasted time re-investigating solved problems.
**Rule for Gollum:** Keep vault files current. After notable events (source blocked, new source discovered, truth filter adjustment, unusual scrape results), update LEARNING-LOG.md immediately. Stale vault = stale agent. When Gollum restarts, the vault files are the ONLY memory that persists.
**Applies to:** LOOP.md Phase 6 (reflect) — write back immediately, don't batch

### LESSON G-010: Source Verification Must Be Continuous (from LEARNING-003)
**What happened:** 37 methodology source links were verified live — all passing. But links rot over time. A link working today doesn't mean it works next month.
**Rule for Gollum:** Source health is not a one-time check. Every scrape cycle should note source availability. If a source returns 404, 403, or empty results for 3+ consecutive cycles, flag it as DEGRADED in LEARNING-LOG.md and tried_fixes.jsonl. Sources that were working yesterday can break tomorrow.
**Applies to:** LOOP.md Phase 1 (observe/scrape) and source health monitoring

### LESSON G-011: Cron/Headless Git Auth Requires Special Setup (from LEARNING-001)
**What happened:** SSH git push failed from cron because cron can't access macOS Keychain. Had to use PAT embedded in the remote URL or SSH ed25519 key with no passphrase.
**Rule for Gollum:** When Gollum runs headless (launchd or tmux), git push authentication must work without user interaction. Verify git push works from the exact environment Gollum runs in — not just from Terminal. Test from a fresh tmux session or via launchd to confirm.
**Applies to:** scout.py git operations when running automated

### LESSON G-012: Trace the Full Data Path End-to-End (from CEO-LEARNING-001, CEO-LEARNING-002)
**What happened:** (1) A function existed and was imported but never called in the actual code path. (2) Data files were written to wrong paths because of doubled directory references (`data/data/file.json`).
**Rule for Gollum:** When debugging any data flow issue, trace the full path: where does scout.py write scout-briefing.json? What path does it use? Does that path match where Baggins reads from? Does git add use the correct relative path? A bug in the relationship between files is harder to find than a bug in one file.
**Applies to:** scout.py output paths, git operations, data file locations

---

*12 lessons from V1 operations. Real failures, real cost, real time. Gollum reads these as part of LEARNING-LOG.md tail load at every briefing cycle.*
