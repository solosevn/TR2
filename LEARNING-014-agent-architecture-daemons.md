# LEARNING-014: Agent Architecture & Daemon Management

**Date:** 2026-03-19
**Trigger:** Audit revealed 6 launchd daemons running when only 4 agents should exist. Old scout agent (PID 786) was still alive and interfering. Sitekeeper crashed (exit 1) but no longer needed as standalone agent.
**Severity:** High — orphaned agents waste resources, confuse state, and can interfere with active agents.

---

## The Four Agents (Canonical — Do Not Add Without David's Approval)

| Agent | launchd Label | Script | Purpose |
|-------|---------------|--------|---------|
| **Kennedy** | `com.trainingrun.kennedy` | `agents/kennedy/kennedy.py` | Telegram bot — human interface, article review, morning intelligence |
| **Gollum** | `com.trainingrun.gollum` | `agents/gollum/scout.py` | Content scout — finds stories, writes briefings |
| **Baggins** | `com.trainingrun.baggins` | `agents/baggins/main.py` | Daily news — selects story, writes article, publishes |
| **Gimli** | `com.trainingrun.gimli` | `agents/unified_ddp.py` | Leaderboard — scrapes benchmarks, scores models, pushes data |

No other agents should be registered in launchd. Any new agent (e.g., Elrond) requires explicit creation and approval.

## Retired / Parked Agents

| Agent | Label | Status | Notes |
|-------|-------|--------|-------|
| **Scout** (old) | `com.trainingrun.scout` | **DELETED** (2026-03-19) | Was a standalone content scout before Gollum absorbed its role. Plist removed from ~/Library/LaunchAgents/. |
| **Sitekeeper** | `com.trainingrun.sitekeeper` | **PARKED** (2026-03-19) | Unloaded from launchd. Plist kept in ~/Library/LaunchAgents/ as blueprint for Elrond (future sitekeeper agent). |

## launchd Plist Locations

- **In repo** (`agents/<name>/`): Kennedy, Gollum, Baggins each have a `.plist` file checked into the repo.
- **On Mac** (`~/Library/LaunchAgents/`): The *installed* copy that launchd reads. Must be manually synced when repo plist changes.
- **Gimli**: Has a launchd entry but plist location needs to be confirmed/added to repo.

## Common Failure Modes

### Exit 78 (Baggins)
- macOS exit code 78 = `EX_CONFIG` — configuration error.
- Root cause: Missing vault files (`shared/USER.md`, `shared/REASONING-CHECKLIST.md`) cause context loading to fail, which crashes the main loop.
- Fix: Create the missing files (see Problem #12), then `launchctl unload` + `launchctl load` to restart.

### Exit 0 but Not Running (Gimli)
- Gimli completes its scrape cycle successfully, then attempts `git push`.
- If the local repo has unstaged changes, git push fails and the process exits cleanly (0).
- Gimli does NOT have a persistent loop — it runs once per launchd trigger. If `KeepAlive` is false or the script exits 0, launchd won't restart it until next trigger.
- Fix: Either add `KeepAlive: true` + a sleep loop, or ensure the git working tree is clean before Gimli runs.

### Orphaned Agents
- When an agent is superseded (e.g., Scout → Gollum), the old launchd plist must be explicitly unloaded AND removed.
- `launchctl unload` stops the daemon. `rm` the plist prevents it from coming back on reboot.
- Always verify with `launchctl list | grep trainingrun` after changes.

## Verification Commands

```bash
# Show all TR2 agents and their state
launchctl list | grep trainingrun

# Show running agent processes
ps aux | grep -E "kennedy|baggins|gollum|gimli" | grep -v grep

# Restart a crashed agent
launchctl unload ~/Library/LaunchAgents/com.trainingrun.<name>.plist
launchctl load ~/Library/LaunchAgents/com.trainingrun.<name>.plist
```

## Rule for Future Agents

Before ANY new agent is registered in launchd:
1. Code must exist in `agents/<name>/` in the TR2 repo
2. Plist must be checked into the repo alongside the code
3. David must approve the agent name and purpose
4. The agent must appear in this LEARNING doc's canonical table
5. Old agents being replaced must be explicitly unloaded + removed

---

**Root cause:** No single document defined which agents should exist. Orphaned daemons accumulated silently.
**Fix:** This document is now the canonical reference. Four agents. No more, no less, unless David says otherwise.
