"""
Kennedy — Media Director Agent
================================
Main agent script. Runs as a Telegram bot + scheduled loop.

L4 Internal / L2 External:
- Autonomous self-improvement, measurement, strategy
- All public content requires David's approval via @KennedyMBot

Powered by Grok 4 (strategy) + Grok 4.1 Fast (operations) via xAI API.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import (
    KENNEDY_BOT_TOKEN, DAVID_CHAT_ID, XAI_API_KEY,
    GROK_API_BASE, GROK_MODEL, GROK_FAST_MODEL,
    ACTIVE_HOURS_START, ACTIVE_HOURS_END,
    LOG_FILE, AGENT_DIR, SCOUT_BRIEFING_PATH,
    BAGGINS_COMMS_DIR, BAGGINS_PENDING_REVIEW, BAGGINS_APPROVAL_PATH,
    BAGGINS_PUBLISHED_PATH, BAGGINS_LOG,
    GOLLUM_SCOUT_LOG,
)
from kennedy_context_loader import load_full_context, build_system_prompt
from kennedy_learning_logger import (
    log_experiment, log_reflection, log_error, log_run,
    update_health_state, log_huddle,
)

# ──────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("kennedy")

# ──────────────────────────────────────────────────────────
# GROK API CLIENT
# ──────────────────────────────────────────────────────────
grok_client = None
if XAI_API_KEY:
    grok_client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)
    logger.info("Grok API client initialized")
else:
    logger.error("XAI_API_KEY not set — Kennedy cannot reason")

# Global state
halted = False
hold_publishing = False
agent_context = {}
pending_article = None  # Tracks current pending review from Baggins
last_pending_check = None  # Timestamp of last pending_review.json we notified David about


# ──────────────────────────────────────────────────────────
# GROK API CALLS
# ──────────────────────────────────────────────────────────

def ask_grok(prompt: str, mode: str = "operations", max_tokens: int = 2000) -> str:
    """
    Send a prompt to Grok and get a response.

    Args:
        prompt: The user/task prompt
        mode: "strategy" (Grok 4) or "operations" (Grok 4.1 Fast)
        max_tokens: Maximum response length
    """
    if not grok_client:
        logger.error("Grok client not initialized")
        return "[ERROR: Grok API not available]"

    model = GROK_MODEL if mode == "strategy" else GROK_FAST_MODEL
    system_prompt = build_system_prompt(agent_context, mode=mode)

    try:
        response = grok_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Grok API error ({model}): {e}")
        log_error(str(e), f"Grok API call failed (model={model})", "", "Check rate limits")
        return f"[ERROR: {e}]"


# ──────────────────────────────────────────────────────────
# TELEGRAM HANDLERS
# ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if update.effective_chat.id != DAVID_CHAT_ID:
        return
    await update.message.reply_text(
        "Kennedy online. Media Director for TrainingRun 2.0.\n\n"
        "Article Review:\n"
        "/approve — Publish Baggins' pending article\n"
        "/reject — Kill the article\n"
        "(Or reply with edit notes)\n\n"
        "Operations:\n"
        "/status — Current health and metrics\n"
        "/hold — Pause all publishing\n"
        "/resume — Resume operations\n"
        "/strategy — Current content strategy\n"
        "/experiments — Last 10 experiment results\n"
        "HALT — Emergency stop"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command — report current health."""
    if update.effective_chat.id != DAVID_CHAT_ID:
        return

    health = agent_context.get("health", {})
    status_msg = (
        f"Kennedy Status Report\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {health.get('status', 'unknown')}\n"
        f"Content on schedule: {health.get('content_on_schedule', 'N/A')}\n"
        f"Engagement trend: {health.get('engagement_trend', 'N/A')}\n"
        f"Active platforms: {', '.join(health.get('platforms_active', []))}\n"
        f"Experiments this week: {health.get('experiments_completed_this_week', 0)}\n"
        f"Top platform: {health.get('top_performing_platform', 'N/A')}\n"
        f"Top content type: {health.get('top_performing_content_type', 'N/A')}\n"
        f"Issues: {len(health.get('issues', []))}\n"
        f"Halted: {halted}\n"
        f"Publishing hold: {hold_publishing}"
    )
    await update.message.reply_text(status_msg)


async def cmd_hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hold command — pause publishing."""
    global hold_publishing
    if update.effective_chat.id != DAVID_CHAT_ID:
        return
    hold_publishing = True
    logger.info("HOLD received from David — publishing paused")
    await update.message.reply_text("Publishing paused. Measurement and learning continue. Send /resume to restart.")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command — resume operations."""
    global halted, hold_publishing
    if update.effective_chat.id != DAVID_CHAT_ID:
        return
    halted = False
    hold_publishing = False
    logger.info("RESUME received from David — all operations resumed")
    await update.message.reply_text("All operations resumed. Kennedy is active.")


async def cmd_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /strategy command — summarize current content strategy."""
    if update.effective_chat.id != DAVID_CHAT_ID:
        return

    response = ask_grok(
        "Summarize my current content strategy in 5 bullet points based on "
        "my recent experiment results and learning log. What's working? What should I do more of?",
        mode="strategy"
    )
    await update.message.reply_text(f"Current Strategy:\n\n{response}")


async def cmd_experiments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /experiments command — show last 10 results."""
    if update.effective_chat.id != DAVID_CHAT_ID:
        return

    results = agent_context.get("memory", {}).get("results_tsv", "No experiments yet.")
    await update.message.reply_text(f"Last experiments:\n\n```\n{results}\n```", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all non-command messages from David."""
    global halted
    if update.effective_chat.id != DAVID_CHAT_ID:
        return

    text = update.message.text.strip() if update.message.text else ""

    # HALT — emergency stop
    if text.upper() == "HALT":
        halted = True
        logger.warning("HALT received from David — all operations stopped")
        log_run("halt", 0, "HALT received", "Emergency stop by David")
        await update.message.reply_text(
            "HALT received. All operations stopped.\n"
            "Send /resume to restart."
        )
        return

    # Normal message — process as a request from David
    if halted:
        await update.message.reply_text("Kennedy is halted. Send /resume to restart operations.")
        return

    # If there's a pending article and David sends a message, treat it as edit notes
    if pending_article and text:
        write_baggins_approval("edit", notes=text)
        paper = pending_article.get("paper_number", "?")
        await update.message.reply_text(
            f"Got it. Sending edit notes to Baggins for Paper {paper:03d}.\n"
            f"He'll revise and send it back."
        )
        logger.info(f"David sent edit notes for Paper {paper:03d}: {text[:100]}")
        return

    # Use Grok to interpret and respond to David's message
    response = ask_grok(
        f"David sent this message via Telegram: \"{text}\"\n\n"
        f"Interpret his intent (he uses voice-to-text, expect typos). "
        f"If it's a request, explain what you'll do. If it's a question, answer it. "
        f"Be concise and direct — David doesn't want lengthy responses.",
        mode="operations"
    )
    await update.message.reply_text(response)


# ──────────────────────────────────────────────────────────
# NOTIFICATION HELPERS
# ──────────────────────────────────────────────────────────

async def send_to_david(app: Application, message: str):
    """Send a message to David via Telegram."""
    try:
        await app.bot.send_message(chat_id=DAVID_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


# ──────────────────────────────────────────────────────────
# BAGGINS MONITORING — Article review flow
# ──────────────────────────────────────────────────────────

def check_baggins_pending():
    """Read Baggins' pending_review.json if it exists."""
    if not BAGGINS_PENDING_REVIEW.exists():
        return None
    try:
        with open(BAGGINS_PENDING_REVIEW) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def write_baggins_approval(action: str, notes: str = ""):
    """Write approval.json for Baggins to pick up."""
    approval = {
        "action": action,
        "notes": notes,
        "from": "kennedy",
        "timestamp": datetime.now().isoformat(),
    }
    BAGGINS_COMMS_DIR.mkdir(exist_ok=True)
    with open(BAGGINS_APPROVAL_PATH, "w") as f:
        json.dump(approval, f, indent=2)
    logger.info(f"Wrote approval for Baggins: {action} {notes[:50] if notes else ''}")


def format_pending_review(pending: dict) -> str:
    """Format a pending review into a Telegram message for David."""
    paper = pending.get("paper_number", "?")
    headline = pending.get("headline", "No headline")
    subtitle = pending.get("subtitle", "")
    category = pending.get("category", "")
    reasoning = pending.get("reasoning", "")
    runner_up = pending.get("runner_up", "")
    status = pending.get("status", "pending_review")
    edit_count = pending.get("edit_count", 0)

    msg = (
        f"{'REVISED ' if status == 'revised' else ''}ARTICLE FOR REVIEW\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Paper {paper:03d}: {headline}\n"
    )
    if subtitle:
        msg += f"{subtitle}\n"
    msg += f"\nCategory: {category}\n"
    if reasoning:
        msg += f"\nWhy this story: {reasoning[:300]}\n"
    if runner_up:
        msg += f"Runner-up: {runner_up[:150]}\n"
    if edit_count:
        msg += f"\nEdit #{edit_count}\n"
    msg += (
        f"\n━━━━━━━━━━━━━━━━━━━\n"
        f"/approve — Publish it\n"
        f"/reject — Kill it\n"
        f"Or reply with edit notes"
    )
    return msg


async def notify_pending_review(app: Application, pending: dict):
    """Send Baggins' pending article to David for review."""
    global pending_article, last_pending_check
    pending_article = pending
    last_pending_check = pending.get("timestamp", "")
    msg = format_pending_review(pending)
    await send_to_david(app, msg)
    logger.info(f"Sent pending review to David — Paper {pending.get('paper_number', '?')}")


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command — approve Baggins' pending article."""
    if update.effective_chat.id != DAVID_CHAT_ID:
        return
    if not pending_article:
        await update.message.reply_text("No article pending review.")
        return
    write_baggins_approval("approve")
    paper = pending_article.get("paper_number", "?")
    await update.message.reply_text(f"Paper {paper:03d} approved. Baggins is publishing.")
    logger.info(f"David approved Paper {paper:03d}")


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reject command — reject Baggins' pending article."""
    global pending_article
    if update.effective_chat.id != DAVID_CHAT_ID:
        return
    if not pending_article:
        await update.message.reply_text("No article pending review.")
        return
    write_baggins_approval("reject")
    paper = pending_article.get("paper_number", "?")
    pending_article = None
    await update.message.reply_text(f"Paper {paper:03d} rejected. Baggins cycle ended.")
    logger.info(f"David rejected Paper {paper:03d}")


# ──────────────────────────────────────────────────────────
# MAIN LOOP CYCLE
# ──────────────────────────────────────────────────────────

async def run_cycle(app: Application):
    """
    Run one full Kennedy cycle:
    1. Load context (vault + memory)
    2. Check time (active hours only)
    3. Determine what to do this cycle
    4. Execute
    5. Log results
    """
    global agent_context

    if halted:
        logger.info("Kennedy is halted — skipping cycle")
        return

    cycle_start = time.time()

    # Step 1: Load context
    agent_context = load_full_context()
    logger.info("Context loaded — starting cycle")

    # Step 2: Check active hours
    current_hour = datetime.now().hour
    if current_hour < ACTIVE_HOURS_START or current_hour >= ACTIVE_HOURS_END:
        logger.info(f"Outside active hours ({current_hour}h) — sleeping")
        return

    # Step 3: Determine cycle type based on time
    if current_hour == 6 and datetime.now().minute < 30:
        cycle_type = "morning_intel"
    elif current_hour == 6:
        cycle_type = "huddle"
    elif current_hour == 7 and datetime.now().minute < 30:
        cycle_type = "gandalf_report"
    elif current_hour == 9:
        cycle_type = "measurement"
    elif current_hour == 21:
        cycle_type = "reflection"
    else:
        cycle_type = "distribution"

    logger.info(f"Cycle type: {cycle_type}")

    # Step 4: Execute cycle
    try:
        if cycle_type == "morning_intel":
            await morning_intelligence(app)
        elif cycle_type == "huddle":
            await daily_huddle(app)
        elif cycle_type == "gandalf_report":
            await gandalf_report(app)
        elif cycle_type == "measurement":
            await measurement_cycle(app)
        elif cycle_type == "reflection":
            await reflection_cycle(app)
        else:
            await distribution_cycle(app)
    except Exception as e:
        logger.error(f"Cycle error ({cycle_type}): {e}")
        log_error(str(e), f"Cycle {cycle_type} failed", "", "Check logs")

    # Step 5: Log the run
    duration = time.time() - cycle_start
    log_run(cycle_type, duration, "completed", "")
    logger.info(f"Cycle {cycle_type} completed in {duration:.1f}s")


# ──────────────────────────────────────────────────────────
# CYCLE IMPLEMENTATIONS (stubs — Kennedy builds these out)
# ──────────────────────────────────────────────────────────

async def morning_intelligence(app: Application):
    """6:00 AM — Read Gollum's briefing, pull platform metrics."""
    logger.info("Morning intelligence gathering")

    # Read Gollum's scout briefing
    intel_parts = []
    if SCOUT_BRIEFING_PATH.exists():
        try:
            with open(SCOUT_BRIEFING_PATH) as f:
                briefing = json.load(f)
            story_count = len(briefing.get("stories", []))
            brief_date = briefing.get("date", "unknown")
            sources = briefing.get("sources_checked", 0)
            intel_parts.append(
                f"Gollum's briefing ({brief_date}): {story_count} stories from {sources} sources"
            )
            # Top 3 stories summary
            for i, story in enumerate(briefing.get("stories", [])[:3]):
                title = story.get("title", "")[:80]
                source = story.get("source", "")
                intel_parts.append(f"  {i+1}. {title} ({source})")
        except (json.JSONDecodeError, IOError) as e:
            intel_parts.append(f"Gollum briefing read error: {e}")
    else:
        intel_parts.append("No scout briefing found — Gollum may not have run yet")

    # Check Baggins status
    if BAGGINS_LOG.exists():
        try:
            lines = BAGGINS_LOG.read_text().strip().split("\n")[-5:]
            last_line = lines[-1] if lines else "No recent activity"
            intel_parts.append(f"\nBaggins last activity: {last_line[:120]}")
        except IOError:
            intel_parts.append("Could not read Baggins log")

    morning_msg = "Good morning. Here's today's intelligence:\n\n" + "\n".join(intel_parts)
    await send_to_david(app, morning_msg)
    logger.info("Morning intelligence sent to David")


async def daily_huddle(app: Application):
    """6:30 AM — Huddle with Baggins + Oden."""
    logger.info("Daily huddle with content team")
    # TODO: Read Baggins' health_state.json
    # TODO: Read Oden's health_state.json (when built)
    # TODO: Generate huddle summary via Grok 4
    # TODO: Write coaching insights to team LEARNING-LOGs
    log_huddle("kennedy", ["baggins"], learnings=["First huddle — establishing baseline"])


async def gandalf_report(app: Application):
    """7:00 AM — Report to Gandalf."""
    logger.info("Reporting to Gandalf")
    # TODO: Generate media arm health summary
    # TODO: Write to Gandalf's huddle input
    # TODO: Check for Gandalf directives


async def distribution_cycle(app: Application):
    """Throughout day — distribute content to platforms."""
    if hold_publishing:
        logger.info("Publishing on hold — skipping distribution")
        return

    logger.info("Content distribution cycle")

    # Check for pending article from Baggins
    pending = check_baggins_pending()
    if pending:
        pending_ts = pending.get("timestamp", "")
        if pending_ts != last_pending_check:
            # New or updated pending review — notify David
            await notify_pending_review(app, pending)
        else:
            logger.info("Pending review already sent to David — waiting for response")
    else:
        logger.info("No pending articles from Baggins")

    # Check if Baggins published something (for social distribution)
    if BAGGINS_PUBLISHED_PATH.exists():
        try:
            with open(BAGGINS_PUBLISHED_PATH) as f:
                published = json.load(f)
            if published.get("status") == "published":
                headline = published.get("headline", "")
                url = published.get("url", "")
                logger.info(f"Baggins published: {headline}")
                # TODO: Generate platform-specific posts via Grok
                # TODO: Post to X, Reddit, etc. with UTM tracking
                # TODO: Log experiment to results.tsv
        except (json.JSONDecodeError, IOError):
            pass


async def measurement_cycle(app: Application):
    """9:00 AM — Measure engagement on yesterday's posts."""
    logger.info("Measurement cycle")
    # TODO: Poll X API for engagement on yesterday's posts
    # TODO: Poll Reddit API for post performance
    # TODO: Read Google Analytics for UTM-tagged traffic
    # TODO: Calculate metrics per platform/content type
    # TODO: Log to results.tsv
    # TODO: Update health_state.json


async def reflection_cycle(app: Application):
    """9:00 PM — End of day reflection."""
    logger.info("End of day reflection")
    # TODO: Summarize today's experiments
    # TODO: Identify patterns
    # TODO: Write to reflection_log.jsonl
    # TODO: Update LEARNING-LOG.md if patterns found
    # TODO: Update health_state.json
    # TODO: Check if 10 experiments reached → write to Red Book
    update_health_state({"last_reflection": datetime.now().isoformat()})


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────

def main():
    """Start Kennedy."""
    logger.info("=" * 60)
    logger.info("Kennedy — Media Director — Starting up")
    logger.info("=" * 60)

    if not KENNEDY_BOT_TOKEN:
        logger.error("KENNEDY_BOT_TOKEN not set — cannot start Telegram bot")
        sys.exit(1)

    if not XAI_API_KEY:
        logger.error("XAI_API_KEY not set — Kennedy cannot reason")
        sys.exit(1)

    # Load initial context
    global agent_context
    agent_context = load_full_context()
    logger.info(f"Initial context loaded — {len(agent_context['vault'])} vault files")

    # Build Telegram application
    app = Application.builder().token(KENNEDY_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("hold", cmd_hold))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("strategy", cmd_strategy))
    app.add_handler(CommandHandler("experiments", cmd_experiments))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    logger.info("Kennedy is live on @KennedyMBot — waiting for David")
    update_health_state({"status": "online", "boot_time": datetime.now().isoformat()})

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
