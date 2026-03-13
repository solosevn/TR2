# CADENCE — Kennedy, Media Director

> **Version:** 1.0 — March 13, 2026

---

## Daily Schedule (CST)

| Time | Activity | Type |
|---|---|---|
| **5:30 AM** | Gollum delivers scout-briefing.json | Dependency (upstream) |
| **6:00 AM** | Kennedy boots — loads vault, memory, reads briefing, pulls platform metrics | Automated |
| **6:30 AM** | Daily huddle with Baggins + Oden | Orchestration |
| **7:00 AM** | Report to Gandalf (CEO huddle) | Reporting |
| **7:30 AM** | First content distribution cycle — post morning content to platforms | Execution |
| **9:00 AM** | Measurement cycle — check 24h metrics on yesterday's posts | Measurement |
| **12:00 PM** | Midday check — any breaking news from Gollum? New benchmark data? | Reactive |
| **3:00 PM** | Afternoon distribution — second content push if warranted | Execution |
| **6:00 PM** | Evening measurement — check engagement on morning posts | Measurement |
| **9:00 PM** | End of day reflection — log experiments, update health_state.json | Reflection |
| **9:30 PM** | Sleep until next boot | — |

## Wake/Sleep Cycle

- **Active hours:** 6:00 AM – 9:30 PM CST
- **Sleep hours:** 9:30 PM – 6:00 AM CST
- **Heartbeat interval during active hours:** Every 30 minutes (launchd)
- **Full cycle:** Boot → check → act → measure → reflect → sleep

## Weekly Schedule

| Day | Special Activity |
|---|---|
| **Monday** | Weekly strategy review — analyze full week of experiment data, adjust content strategy |
| **Wednesday** | Self-improvement window — review results.tsv, identify code improvements, run L4 experiments |
| **Friday** | Weekly report to Gandalf — comprehensive media arm health, trends, learnings |
| **Sunday** | Reduced cadence — measurement only, no new posts (unless breaking news) |

## Dependencies

| Agent | What Kennedy Receives | When |
|---|---|---|
| **Gollum** | scout-briefing.json (trending AI topics) | 5:30 AM daily |
| **Baggins** | Article status, published articles | 6:30 AM huddle |
| **Gimli** | TRSbench scoring data (new benchmark results) | After 4:00 AM DDP run |
| **Gandalf** | Company-wide directives, priority overrides | 7:00 AM huddle |

## Triggers (outside of schedule)

- **Gollum flags HIGH priority story** → Kennedy enters Reactive mode immediately
- **Gimli completes benchmark cycle** → Kennedy generates distribution posts
- **David messages @KennedyMBot** → Kennedy responds immediately (interrupt any non-critical task)
- **HALT command** → Kennedy stops all operations immediately

## launchd Configuration

- **Plist:** `com.trainingrun.kennedy.plist`
- **RunAtLoad:** true
- **StartInterval:** 1800 (30 minutes)
- **Active hours enforcement:** kennedy.py checks current time at boot, sleeps if outside 6AM-9:30PM
