#!/usr/bin/env python3
"""
Daily News Agent — Main Orchestrator
======================================
The execution engine for TrainingRun.AI's autonomous journalist.

This agent:
  1. Listens for Content Scout's morning briefing (via local file)
  2. Selects the best story using Grok + David's 5-filter test
  3. Writes a full article in David's voice using Grok
  4. Stages the HTML and writes pending review for Kennedy (file-based)
  5. Waits for Kennedy's approval (push it / edit / kill it)
  6. Publishes to GitHub on approval
  7. Logs everything for the learning engine

Run:    python3 main.py
Test:   python3 main.py --test
Dry:    python3 main.py --dry-run
Status: python3 main.py --check

Reads instructions from context-vault files:
  SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md, STYLE-EVOLUTION.md, USER.md
"""

import os
import sys
import json
import time
import logging
import datetime
import argparse
from pathlib import Path

# Agent modules
from config import (
    XAI_API_KEY, GITHUB_TOKEN,
    COMMS_DIR, PENDING_REVIEW_PATH, APPROVAL_PATH,
    SCOUT_BRIEFING_PATH, STAGING_DIR, LOG_FILE, POLL_INTERVAL_SECONDS,
    APPROVAL_TIMEOUT_MINUTES,
)
from context_loader import load_all_context, load_scout_briefing, get_stories_from_briefing
from story_selector import select_story
from article_writer import write_article, revise_article
from html_stager import stage_article, get_next_paper_number, build_news_card
from github_publisher import publish_article, commit_vault_file
from learning_logger import log_to_run_log, log_to_learning_log, commit_logs

# ──────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("DailyNewsAgent")


# ──────────────────────────────────────────────────────────
# AGENT STATE
# ──────────────────────────────────────────────────────────

class AgentState:
    """Tracks the agent's current workflow state."""

    IDLE = "IDLE"
    SELECTING = "SELECTING"
    WRITING = "WRITING"
    STAGING = "STAGING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EDITING = "EDITING"
    PUBLISHING = "PUBLISHING"
    LOGGING = "LOGGING"

    def __init__(self):
        self.state = self.IDLE
        self.context = {}           # Loaded vault files
        self.briefing = {}          # Content Scout's briefing
        self.stories = []           # Parsed story list
        self.selection = {}         # Selected story + reasoning
        self.article = {}           # Written article data
        self.staged = {}            # Staged HTML data
        self.paper_number = 0
        self.edit_count = 0
        self.edit_notes = []
        self.cycle_start = None
        self.phase_times = {}       # Timing per phase
        self.dry_run = False

    def reset(self):
        """Reset state for a new cycle."""
        self.__init__()


# Global agent state
agent = AgentState()


# ──────────────────────────────────────────────────────────
# WORKFLOW — The 15-step PROCESS.md as code
# ──────────────────────────────────────────────────────────

def run_workflow(dry_run=False):
    """
    Execute the full Daily News Agent workflow.
    Follows PROCESS.md V3.0 steps 1-15.
    """
    agent.dry_run = dry_run
    agent.cycle_start = time.time()

    try:
        # ── Step 1: Content Scout delivers stories ──
        logger.info("═══ DAILY NEWS AGENT — CYCLE START ═══")
        agent.state = AgentState.SELECTING

        # ── Step 2: Load context vault ──
        logger.info("Loading context vault...")
        agent.context = load_all_context()
        logger.info(f"Context loaded: {len(agent.context)} files")

        # ── Step 3: Read Content Scout's briefing ──
        logger.info("Reading Content Scout briefing...")
        agent.briefing = load_scout_briefing()
        agent.stories = get_stories_from_briefing(agent.briefing)

        if not agent.stories:
            # Check briefing freshness and time-based deadline
            now = datetime.datetime.now()
            briefing_file = Path(SCOUT_BRIEFING_PATH)
            briefing_age_msg = ""
            if briefing_file.exists():
                mtime = datetime.datetime.fromtimestamp(briefing_file.stat().st_mtime)
                hours_old = (now - mtime).total_seconds() / 3600
                briefing_age_msg = f" (briefing file is {hours_old:.1f}h old)"
            else:
                briefing_age_msg = " (no briefing file found)"

            is_past_deadline = (now.hour > 5) or (now.hour == 5 and now.minute >= 45)

            if is_past_deadline:
                alert = (
                    "⚠️ DAILY NEWS AGENT — 5:45 AM DEADLINE\n\n"
                    f"No Content Scout briefing received{briefing_age_msg}.\n"
                    "Content Scout may have failed or not run yet.\n\n"
                    "Options:\n"
                    "• Check Content Scout: cd ~/Desktop/TR2 && python3 agents/content-scout/scout.py\n"
                    "• Manual trigger: restart Daily News Agent after scout runs"
                )
                logger.warning(f"DEADLINE ALERT: No briefing by 5:45 AM{briefing_age_msg}")
            else:
                logger.warning("No stories found in briefing. Waiting for Content Scout.")
            return

        logger.info(f"Found {len(agent.stories)} stories from Content Scout")

        # ── Step 4-5: Select best story (5-filter test + REASONING-CHECKLIST) ──
        phase_start = time.time()
        logger.info("Selecting best story via Grok...")
        agent.selection = select_story(
            stories=agent.stories,
            user_md=agent.context.get("user_md", ""),
            style_md=agent.context.get("style_md", ""),
            reasoning_md=agent.context.get("reasoning_md", ""),
            learning_md=agent.context.get("learning_md", ""),
            run_log_md=agent.context.get("run_log_md", ""),
        )
        agent.phase_times["selection"] = (time.time() - phase_start) / 60

        if agent.selection.get("error"):
            logger.error(f"Story selection failed: {agent.selection['error']}")
            return

        logger.info(f"Selected: {agent.selection.get('title', 'Unknown')} ({agent.phase_times['selection']:.1f} min)")

        # ── Step 6: Write article via Grok ──
        agent.state = AgentState.WRITING
        phase_start = time.time()
        logger.info("Writing article via Grok...")

        selected_story = agent.stories[agent.selection.get("story_index", 0)]
        agent.article = write_article(
            story=selected_story,
            selection=agent.selection,
            user_md=agent.context.get("user_md", ""),
            style_md=agent.context.get("style_md", ""),
            learning_md=agent.context.get("learning_md", ""),
            engagement_md=agent.context.get("engagement_md", ""),
        )
        agent.phase_times["writing"] = (time.time() - phase_start) / 60

        if agent.article.get("error"):
            logger.error(f"Article writing failed: {agent.article['error']}")
            return

        logger.info(f"Article written: '{agent.article.get('headline', '')}' ({agent.phase_times['writing']:.1f} min)")

        # ── Step 7: Stage HTML ──
        agent.state = AgentState.STAGING
        phase_start = time.time()
                # -- Step 6b: Generate article image via Grok --
        logger.info("Generating article image via Grok...")
        from image_generator import generate_image, download_image
        image_result = generate_image(
            headline=agent.article.get("headline", ""),
            subtitle=agent.article.get("subtitle", ""),
            category=agent.article.get("category", "AI Research"),
            article_html=agent.article.get("article_html", ""),
        )
        if image_result.get("error"):
            logger.warning(f"Image generation failed (non-fatal): {image_result['error']}")
        else:
            agent.article["image_url"] = image_result["image_url"]
            agent.article["image_caption"] = image_result["image_caption"]
            logger.info("Article image generated successfully")

        # Enrich article data for stager
        agent.article["story_url"] = selected_story.get("url", "")
        agent.article["story_title"] = selected_story.get("title", "")

        agent.paper_number = get_next_paper_number()
        logger.info(f"Staging as Paper {agent.paper_number:03d}...")

        agent.staged = stage_article(agent.article, agent.paper_number)
        agent.phase_times["staging"] = (time.time() - phase_start) / 60

        logger.info(f"Staged: {agent.staged.get('filename', '')} ({agent.phase_times['staging']:.1f} min)")

        # ── Step 8: Write pending review for Kennedy ──
        agent.state = AgentState.AWAITING_APPROVAL

        if dry_run:
            logger.info("[DRY RUN] Would write pending review for Kennedy")
            logger.info(f"[DRY RUN] Headline: {agent.article.get('headline', '')}")
            logger.info(f"[DRY RUN] Staged at: {agent.staged.get('local_path', '')}")
            logger.info("═══ DRY RUN COMPLETE ═══")
            _print_cycle_summary()
            return

        logger.info("Writing pending review for Kennedy...")

        # Write pending review for Kennedy
        pending = {
            "status": "pending_review",
            "paper_number": agent.paper_number,
            "headline": agent.article.get("headline", ""),
            "subtitle": agent.article.get("subtitle", ""),
            "category": agent.article.get("category", "AI Research"),
            "reasoning": agent.selection.get("reasoning", ""),
            "runner_up": agent.selection.get("runner_up", ""),
            "article_preview": agent.article.get("article_html", "")[:800],
            "image_url": agent.article.get("image_url", ""),
            "staged_file": agent.staged.get("filename", ""),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        with open(PENDING_REVIEW_PATH, "w") as f:
            json.dump(pending, f, indent=2)
        logger.info(f"Pending review written for Kennedy — Paper {agent.paper_number:03d}")

        logger.info("⏳ Waiting for Kennedy's response...")
        # Response handling happens in the main loop (check_for_approval)

    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)


def handle_approval(action: str, notes: str = ""):
    """
    Handle Kennedy's response to the review request.
    Called from the main loop.
    """
    if action == "approve":
        # ── Step 11-14: Publish ──
        do_publish()

    elif action == "edit":
        # ── Step 10: Revision cycle ──
        do_edit(notes)

    elif action == "reject":
        # Kill it
        logger.info("Kennedy rejected the article. Cycle ended.")
        agent.state = AgentState.IDLE


def do_edit(notes: str):
    """Handle an edit request from Kennedy."""
    agent.state = AgentState.EDITING
    agent.edit_count += 1
    agent.edit_notes.append(notes)
    logger.info(f"Edit #{agent.edit_count} requested: {notes}")

    # Revise via Grok
    revision = revise_article(
        original_html=agent.article.get("article_html", ""),
        edit_notes=notes,
        user_md=agent.context.get("user_md", ""),
    )

    if revision.get("error"):
        logger.error(f"Revision failed: {revision['error']}")
        return

    # Update article with revision
    agent.article["article_html"] = revision["article_html"]

    # Re-stage
    agent.staged = stage_article(agent.article, agent.paper_number)

    # Update pending review with revision
    agent.state = AgentState.AWAITING_APPROVAL
    pending = {
        "status": "revised",
        "paper_number": agent.paper_number,
        "headline": agent.article.get("headline", ""),
        "subtitle": agent.article.get("subtitle", ""),
        "category": agent.article.get("category", "AI Research"),
        "reasoning": agent.selection.get("reasoning", ""),
        "runner_up": agent.selection.get("runner_up", ""),
        "article_preview": agent.article.get("article_html", "")[:800],
        "image_url": agent.article.get("image_url", ""),
        "staged_file": agent.staged.get("filename", ""),
        "edit_count": agent.edit_count,
        "edit_notes": notes,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    with open(PENDING_REVIEW_PATH, "w") as f:
        json.dump(pending, f, indent=2)
    logger.info(f"Revised article staged — edit #{agent.edit_count}")


def do_publish():
    """Publish the approved article."""
    agent.state = AgentState.PUBLISHING
    phase_start = time.time()
    logger.info(f"Publishing Paper {agent.paper_number:03d}...")

    # Publish to GitHub
    pub_result = publish_article(
        article_filename=agent.staged["filename"],
        article_html=agent.staged["html_content"],
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
    )

    agent.phase_times["approval"] = (time.time() - (agent.phase_times.get("_approval_start", phase_start))) / 60

    if pub_result.get("errors"):
        for err in pub_result["errors"]:
            logger.error(err)
        return

    for step in pub_result.get("steps", []):
        logger.info(step)

    # ── Step 13: Commit image to GitHub if we have one ──
    if agent.article.get("image_url"):
        from image_generator import download_image, commit_image_to_github
        image_bytes = download_image(agent.article["image_url"])
        if image_bytes:
            img_result = commit_image_to_github(image_bytes, agent.paper_number)
            if img_result.get("error"):
                logger.warning(f"Image commit failed (non-fatal): {img_result['error']}")
            else:
                logger.info(f"Image committed: {img_result['image_path']}")

    article_url = pub_result.get("article_url", f"https://trainingrun.ai/{agent.staged['filename']}")

    # Write published confirmation
    published = {
        "status": "published",
        "paper_number": agent.paper_number,
        "headline": agent.article.get("headline", ""),
        "url": article_url,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    with open(COMMS_DIR / "published.json", "w") as f:
        json.dump(published, f, indent=2)

    # Clear pending review
    if PENDING_REVIEW_PATH.exists():
        PENDING_REVIEW_PATH.unlink()
    if APPROVAL_PATH.exists():
        APPROVAL_PATH.unlink()

    # ── Step 14-15: Log to learning engine ──
    agent.state = AgentState.LOGGING
    logger.info("Logging to learning engine...")

    total_cycle = (time.time() - agent.cycle_start) / 60
    first_pass = agent.edit_count == 0

    run_log = log_to_run_log(
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
        source_url=agent.selection.get("url", ""),
        category=agent.article.get("category", "AI Research"),
        cycle_time_minutes=total_cycle,
        edit_count=agent.edit_count,
        first_pass=first_pass,
    )

    learning_log = log_to_learning_log(
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
        selection_time=agent.phase_times.get("selection", 0),
        writing_time=agent.phase_times.get("writing", 0),
        staging_time=agent.phase_times.get("staging", 0),
        approval_time=agent.phase_times.get("approval", 0),
        edit_count=agent.edit_count,
        first_pass=first_pass,
        edit_notes=agent.edit_notes,
    )


    # ─── NEW: Write feedback for Content Scout learning loop ──────
    try:
        scout_feedback = {
            "selected_story_title": agent.selection.get("headline", ""),
            "selected_source": agent.selection.get("source", ""),
            "selected_truth_score": agent.selection.get("truth_score", 0),
            "selected_category": agent.article.get("category", "general"),
            "selected_rank": agent.selection.get("rank", 1),
            "rejected_stories": [
                {
                    "title": s.get("title", ""),
                    "source": s.get("source", ""),
                    "truth_score": s.get("truth_score", 0)
                }
                for s in getattr(agent, "stories", [])
                if s.get("title") != agent.selection.get("headline", "")
            ][:5],
            "paper_number": agent.paper_number,
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        feedback_path = os.path.join(os.path.dirname(SCOUT_BRIEFING_PATH), "scout-feedback.json")
        with open(feedback_path, "w", encoding="utf-8") as fb:
            json.dump(scout_feedback, fb, indent=2)
        logger.info(f"[DailyNews] Wrote scout-feedback.json for Paper {agent.paper_number:03d}")
    except Exception as e:
        logger.warning(f"[DailyNews] Failed to write scout feedback (non-critical): {e}")
    # ─── END NEW ──────────────────────────────────────────────────

    log_result = commit_logs(run_log, learning_log, agent.paper_number)
    for step in log_result.get("steps", []):
        logger.info(step)
    for err in log_result.get("errors", []):
        logger.error(err)

    # Done
    logger.info(f"═══ CYCLE COMPLETE — Paper {agent.paper_number:03d} published in {total_cycle:.1f} min ═══")
    _print_cycle_summary()
    # Mark today as processed (prevents check_for_scout_briefing from re-triggering)
    last_file = STAGING_DIR / ".last_processed_date"
    last_file.write_text(datetime.date.today().isoformat())
    logger.info("Marked today as processed")

    agent.state = AgentState.IDLE


def _print_cycle_summary():
    """Print timing summary to log."""
    logger.info("── Cycle Summary ──")
    for phase, minutes in agent.phase_times.items():
        if not phase.startswith("_"):
            logger.info(f"  {phase}: {minutes:.1f} min")
    logger.info(f"  edits: {agent.edit_count}")


# ──────────────────────────────────────────────────────────
# FILE-BASED POLLING
# ──────────────────────────────────────────────────────────

def check_for_scout_briefing():
    """Check if Content Scout has delivered a fresh briefing."""
    today = datetime.date.today().isoformat()

    # Check if we already processed today
    last_file = STAGING_DIR / ".last_processed_date"
    if last_file.exists() and last_file.read_text().strip() == today:
        return False

    briefing = load_scout_briefing()
    brief_date = briefing.get("date", "")

    if brief_date == today and get_stories_from_briefing(briefing):
        logger.info(f"Fresh Content Scout briefing detected for {today}!")
        return True
    return False


def check_for_approval():
    """Check if Kennedy has written an approval response."""
    if not APPROVAL_PATH.exists():
        return None

    try:
        with open(APPROVAL_PATH) as f:
            approval = json.load(f)
        return approval
    except (json.JSONDecodeError, IOError):
        return None


# ──────────────────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────────────────

def check_config():
    """Verify all required config is present."""
    issues = []
    if not XAI_API_KEY:
        issues.append("XAI_API_KEY not set")
    if not GITHUB_TOKEN:
        issues.append("GITHUB_TOKEN not set")
    return issues


def main():
    """Main entry point — Baggins runs as an autonomous agent daemon."""
    parser = argparse.ArgumentParser(description="Baggins — Daily News Agent for TrainingRun.AI")
    parser.add_argument("--test", action="store_true", help="Test connections and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run workflow without publishing")
    parser.add_argument("--check", action="store_true", help="Check config and exit")
    args = parser.parse_args()

    # Banner
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║   Baggins — Daily News Agent             ║")
    logger.info("║   TrainingRun.AI | Powered by Grok (xAI) ║")
    logger.info("║   Reports to Kennedy via file comms      ║")
    logger.info("╚══════════════════════════════════════════╝")

    # Config check
    issues = check_config()
    if issues:
        for issue in issues:
            logger.error(f"CONFIG ERROR: {issue}")
        if not args.check:
            logger.error("Fix .env file and restart.")
            sys.exit(1)
        return

    logger.info("Config OK")

    if args.check:
        logger.info("Config check passed.")
        return

    # Connection tests
    if args.test:
        logger.info("── Running Connection Tests ──")
        from story_selector import test_grok_connection
        from github_publisher import test_github_connection
        from context_loader import test_context_loader

        results = []
        results.append(("Grok API", test_grok_connection()))
        results.append(("GitHub API", test_github_connection()))
        results.append(("Context Vault", test_context_loader()))

        logger.info("── Test Results ──")
        all_pass = True
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            logger.info(f"  {name}: {status}")
            if not ok:
                all_pass = False

        if all_pass:
            logger.info("All tests passed. Agent is ready.")
        else:
            logger.error("Some tests failed. Fix issues above.")
        return

    # Dry run
    if args.dry_run:
        logger.info("── DRY RUN MODE ──")
        run_workflow(dry_run=True)
        return

    # ── LIVE MODE: Daemon loop ──
    logger.info("Baggins is live — watching for scout briefings and Kennedy's responses...")
    logger.info(f"Comms dir: {COMMS_DIR}")

    while True:
        try:
            # Check for fresh scout briefing
            if agent.state == AgentState.IDLE and check_for_scout_briefing():
                agent.state = AgentState.SELECTING
                run_workflow()
                # After workflow, state is AWAITING_APPROVAL or IDLE

            # Check for Kennedy's approval/edit/reject
            if agent.state == AgentState.AWAITING_APPROVAL:
                approval = check_for_approval()
                if approval:
                    action = approval.get("action", "")
                    notes = approval.get("notes", "")
                    logger.info(f"Kennedy response: {action} {notes[:100] if notes else ''}")

                    # Delete approval file before processing
                    if APPROVAL_PATH.exists():
                        APPROVAL_PATH.unlink()

                    handle_approval(action, notes)

            time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            logger.info("Baggins shutting down.")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
