# LEARNING-005: Kennedy cmd_approve — Missing State Cleanup

## Date
March 17, 2026

## Problem
After David used /approve to approve Paper 012, Kennedy continued treating all subsequent free-text messages as edit notes for Baggins. David's question "is it a good story?" was forwarded to Baggins as "Edit #1" instead of being answered.

## Root Cause
The `cmd_approve()` function in `kennedy.py` wrote the approval to Baggins' approval file but never cleared the `pending_article` global variable. Since `pending_article` remained set, the message handler at line 229 (`if pending_article and text:`) continued intercepting all free-text messages and routing them as edit notes.

Meanwhile, `cmd_reject()` correctly included both:
1. `global pending_article` declaration
2. `pending_article = None` after processing

The approve path was simply missing these two lines — a copy-paste oversight during initial development.

## Fix Applied
Added two lines to `cmd_approve()`:
- Line 337: `global pending_article` (required to modify module-level variable)
- Line 345: `pending_article = None` (clears state after extracting paper number)

Commit: `0995d3c` — "Fix Kennedy cmd_approve: clear pending_article after approval"

## Verification
The fix matches the exact pattern used in `cmd_reject()` (lines 350-362). Both functions now:
1. Declare `global pending_article`
2. Write approval/rejection to Baggins
3. Extract paper number from pending_article
4. Set `pending_article = None`
5. Reply to David
6. Log the action

## Learning for Agents
When a function modifies global state (sets a flag, stores data), every exit path from that state must clean it up. If you have paired operations (approve/reject, open/close, start/stop), they must handle state symmetrically. Always check: "If I wrote a setter, did I write the corresponding unsetter in ALL code paths?"

## Pattern: State Machine Hygiene
```
# BAD — state leak
def approve():
    process(pending)
    reply("done")
    # pending still set! All future messages go to wrong handler

# GOOD — clean state transition
def approve():
    global pending
    process(pending)
    pending = None  # Explicit state transition
    reply("done")
```

## Prevention
- When writing paired command handlers (approve/reject, start/stop), write both at the same time
- Use a checklist: "Does this function clean up every global/module variable it depends on?"
- Add a post-action assertion: if the function's job is done, the state variable should be None
- Consider using a state machine pattern instead of bare globals for complex flows

## Tags
state-management, kennedy, telegram-bot, global-variable, pending-article, approve-reject
