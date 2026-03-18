# LEARNING-013: Kennedy Crash Recovery and Auto-Restart

**Date**: 2026-03-18
**Scope**: Kennedy Telegram bot resilience
**Status**: Implemented

## Problem Statement

Kennedy stopped responding to messages ~10 minutes into operation on 2026-03-17. Possible causes:
1. A Telegram handler crashed silently (no try/except)
2. The polling loop crashed with no restart mechanism
3. A scheduled job (distribution_cycle or run_cycle) raised an exception that killed the polling loop

**Issue**: There was no crash recovery or auto-restart logic. If any handler failed, the entire bot would stop responding to David with no notification.

---

## Solution: Crash Recovery Pattern for Always-On Agents

For L4 autonomous agents running continuously (like Kennedy), here's the resilience pattern:

### 1. Wrap Every Handler in Try/Except

Every async handler (message handlers, command handlers, job queue functions) MUST wrap its logic:

```python
async def some_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # All handler logic here
        if update.effective_chat.id != DAVID_CHAT_ID:
            return
        # ... rest of handler ...
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in some_handler: {e}", exc_info=True)
        log_error(str(e), "some_handler failed", "", "Check logs")
        # Handler continues to exist; next message will be processed normally
```

**Why**: If one bad message crashes a handler, the polling loop itself survives and can handle the next message. The error is logged but doesn't crash the bot.

### 2. Wrap the Polling Loop

The main polling loop (the heartbeat of the bot) must be protected:

```python
try:
    logger.info("Starting polling loop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
except Exception as e:
    logger.error(f"Fatal error in polling loop: {e}", exc_info=True)
    log_error(str(e), "Polling loop crashed", "", "Check logs and restart Kennedy")
    sys.exit(1)
```

If polling crashes, log it and exit cleanly so launchd can restart.

### 3. Wrap Job Queue Functions

Scheduled jobs must not crash the polling loop:

```python
async def _job_distribution(context: ContextTypes.DEFAULT_TYPE):
    try:
        await distribution_cycle(context.application)
    except Exception as e:
        logger.error(f"Error in distribution cycle job: {e}", exc_info=True)
        log_error(str(e), "distribution_cycle job failed", "", "Will retry in 60s")
        # Job queue will call this again in 60s automatically
```

### 4. Wrap main() for Graceful Shutdown

The entry point handles startup errors and keyboard interrupts:

```python
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Kennedy shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        log_error(str(e), "Kennedy startup failed", "", "Check logs")
        sys.exit(1)
```

### 5. Add Heartbeat Logging

Log that the bot is alive at startup. This allows David (or monitoring) to detect if Kennedy has crashed:

```python
# In main(), right after loading context:
logger.info(f"Kennedy heartbeat - startup at {datetime.now().isoformat()}")
```

David can check `tail agents/kennedy/kennedy.log | grep heartbeat` to see if Kennedy restarted recently.

### 6. Configure launchd for Auto-Restart (macOS)

Create `com.trainingrun.kennedy.plist` in the agent directory with:

```xml
<key>KeepAlive</key>
<true/>
<key>ThrottleInterval</key>
<integer>30</integer>
```

**KeepAlive=true**: If Kennedy exits (or crashes), launchd will restart it.
**ThrottleInterval=30**: If Kennedy keeps crashing, wait 30s between restart attempts (prevents restart loops).

macOS then loads this with:
```bash
launchctl load ~/Library/LaunchAgents/com.trainingrun.kennedy.plist
```

---

## Changes Made to Kennedy

### kennedy.py
- **Fixed f-string syntax errors** in `format_pending_review()` (nested ternary expressions in f-strings require intermediate variables)
- **Wrapped job queue functions** (`_job_distribution`, `_job_run_cycle`) in try/except
- **Wrapped main polling loop** in try/except
- **Wrapped main() entry point** in try/except + KeyboardInterrupt
- **Added heartbeat logging** at startup

### com.trainingrun.kennedy.plist
- Created launchd plist with KeepAlive=true for automatic restart on crash
- Configured stdout/stderr logging to track crashes
- Set ThrottleInterval=30 to prevent restart loops

---

## How Kennedy Recovers from Crashes

**Scenario**: David sends a message that causes `ask_grok()` to throw an exception.

1. **Before (no recovery)**:
   - Handler crashes silently
   - Polling loop crashes
   - Kennedy stops responding to messages
   - No notification to David
   - David must manually restart Kennedy

2. **After (with crash recovery)**:
   - Handler catches exception and logs it
   - Polling loop continues running
   - Kennedy processes the next message normally
   - Error is logged to `kennedy.log` and `error_log.jsonl`
   - David can see the error in Kennedy's learning logs
   - Bot stays online

**If the polling loop itself crashes** (rare):
   - Polling wrapper catches the exception and exits cleanly
   - launchd sees the process exited
   - launchd restarts Kennedy automatically (within 30s)
   - Kennedy boots, logs a heartbeat, and is online again
   - David never experienced downtime (launchd handled restart)

---

## Pattern for Future Handlers

Whenever you (Kennedy) add a new handler, wrap it:

```python
async def new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # All logic here
        ...
    except Exception as e:
        logger.error(f"Error in new_handler: {e}", exc_info=True)
        log_error(str(e), "new_handler failed", "", "Check logs")
```

The try/except means:
- **One bad message doesn't crash the bot**
- **Error is logged for learning**
- **Next message is processed normally**
- **System stays resilient**

---

## Monitoring

David can monitor Kennedy's health:

```bash
# Check if Kennedy restarted recently (heartbeat logs)
tail -n 20 agents/kennedy/kennedy.log | grep heartbeat

# Check for errors
tail -n 50 agents/kennedy/memory/error_log.jsonl

# Monitor live
tail -f agents/kennedy/kennedy.log
```

---

## References

- **python-telegram-bot** error handling: https://docs.python-telegram-bot.org/
- **launchd plist reference**: `man launchd.plist` on macOS
- **Python logging best practices**: https://docs.python.org/3/howto/logging.html
