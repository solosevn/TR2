# LEARNING-007: Run Cycle Deduplication

## Problem
Kennedy's `run_cycle()` fires every 300 seconds (5 minutes). Once-daily cycle types like `morning_intel` are triggered by time-window checks (e.g., `current_hour == 6 and minute < 30`). Because the 300s interval fits multiple times within a 30-minute window, the same cycle type fires repeatedly.

**Observed:** Morning intelligence message sent twice — at 6:04 AM and 6:09 AM on March 17, 2026.

## Root Cause
No deduplication guard existed in `run_cycle()`. The function determined the cycle type based on time-of-day, then executed it unconditionally. Every poll cycle that fell within the time window re-triggered the same once-daily action.

## Fix
**Commit:** `e3c8207` — kennedy.py (624 lines)

Added module-level tracking dict and Step 3b dedup guard:

```python
# Module level — tracks which cycle types already ran today
_last_cycle_dates = {}  # {cycle_type: "YYYY-MM-DD"}

# Inside run_cycle(), between Step 3 (determine cycle type) and Step 4 (execute):
# Step 3b: Dedup — skip if this cycle type already ran today
today_str = datetime.now().strftime("%Y-%m-%d")
if cycle_type in ("morning_intel", "huddle", "gandalf_report", "reflection"):
    if _last_cycle_dates.get(cycle_type) == today_str:
        logger.info(f"Cycle {cycle_type} already ran today — skipping")
        return
    _last_cycle_dates[cycle_type] = today_str
```

**How it works:**
- Dict keys are cycle type strings, values are date strings ("YYYY-MM-DD")
- On first execution of a cycle type for the day, the date is stored and execution proceeds
- On subsequent polls within the same time window, the date matches → skip with log
- Resets naturally at midnight because the date string changes
- Only guards once-daily cycles; continuous cycles (like `check_telegram`) are excluded

## Pattern: Polling Loop Deduplication

When a polling loop determines actions by time-window matching, every action that should run at most once per period needs an explicit "already ran" guard.

**Template:**
```python
_execution_tracker = {}  # {action_name: "period_key"}

def poll_loop():
    action = determine_action(current_time)
    period_key = get_period_key()  # e.g., today's date string
    
    if action in ONCE_PER_PERIOD_ACTIONS:
        if _execution_tracker.get(action) == period_key:
            log(f"{action} already ran this period — skipping")
            return
        _execution_tracker[action] = period_key
    
    execute(action)
```

## Prevention Checklist
1. Every polling loop that dispatches time-based actions MUST have a dedup guard
2. The guard must use a stable period key (date string, not timestamp)
3. Log skipped executions so they're visible in debugging
4. Only guard periodic actions — continuous/idempotent actions don't need it
5. Consider: what happens if the process restarts mid-day? (In-memory dict resets, so the action runs once more — acceptable for most cases. If not, persist to disk.)

## Affected Agents
- **Kennedy** — run_cycle() in kennedy.py
- **Any future agent** with a polling loop that dispatches once-daily actions

## Related
- Bug #6 on 2026.03.17 problem list
- LEARNING-008 (pending): Kennedy crash recovery — related to process restart behavior
