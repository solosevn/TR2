"""
Kennedy — Learning Logger
==========================
Post-action: writes to vault + memory files after every action.

Write after acting. This closes the RSI loop.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from config import MEMORY_FILES, VAULT_DIR, TR_REPO_PATH

logger = logging.getLogger("kennedy.learning_logger")


def _now() -> str:
    """Current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, entry: dict):
    """Append a JSON object as a new line to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"Appended to {path.name}")


def _append_tsv(path: Path, row: list):
    """Append a tab-separated row to a TSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\t".join(str(v) for v in row) + "\n")
    logger.info(f"Appended to {path.name}")


def _append_md(path: Path, entry: str):
    """Append a markdown entry to a .md file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{entry}\n")
    logger.info(f"Appended to {path.name}")


# ─────────────────────────────────────────────
# EXPERIMENT LOGGING (results.tsv)
# ─────────────────────────────────────────────

def log_experiment(commit: str, metric_value: str, status: str,
                   description: str, platform: str = "", content_type: str = ""):
    """
    Log an experiment result to results.tsv.

    Args:
        commit: git commit hash or experiment ID
        metric_value: the measured outcome (e.g., "4.2%_ctr")
        status: "keep", "discard", or "crash"
        description: what this experiment tried
        platform: which platform (x, reddit, linkedin, etc.)
        content_type: type of content (benchmark, news, analysis, etc.)
    """
    row = [commit, metric_value, status, description, platform, content_type, _now()]
    _append_tsv(MEMORY_FILES["results_tsv"], row)


# ─────────────────────────────────────────────
# REFLECTION LOGGING
# ─────────────────────────────────────────────

def log_reflection(hypothesis: str, action: str, outcome: str,
                   why: str, next_step: str = ""):
    """Log a reflection after an experiment or observation."""
    entry = {
        "date": _now(),
        "hypothesis": hypothesis,
        "action": action,
        "outcome": outcome,
        "why": why,
        "next_step": next_step,
    }
    _append_jsonl(MEMORY_FILES["reflection_log"], entry)


# ─────────────────────────────────────────────
# ERROR LOGGING
# ─────────────────────────────────────────────

def log_error(error: str, context: str, resolution: str = "", prevention: str = ""):
    """Log an error with context and resolution."""
    entry = {
        "date": _now(),
        "error": error,
        "context": context,
        "resolution": resolution,
        "prevention": prevention,
    }
    _append_jsonl(MEMORY_FILES["error_log"], entry)


# ─────────────────────────────────────────────
# TRIED FIXES LOGGING
# ─────────────────────────────────────────────

def log_tried_fix(action: str, outcome: str, status: str, lesson: str = ""):
    """Log a fix attempt for future reference."""
    entry = {
        "date": _now(),
        "action": action,
        "outcome": outcome,
        "status": status,
        "lesson": lesson,
    }
    _append_jsonl(MEMORY_FILES["tried_fixes"], entry)


# ─────────────────────────────────────────────
# HUDDLE LOGGING
# ─────────────────────────────────────────────

def log_huddle(parent: str, attendees: list, solved: list = None,
               escalated_to_me: list = None, escalated_up: list = None,
               learnings: list = None, action_items: list = None):
    """Log a daily huddle output."""
    entry = {
        "huddle_date": datetime.now().strftime("%Y-%m-%d"),
        "parent": parent,
        "attendees": attendees,
        "solved_at_this_level": solved or [],
        "escalated_to_me": escalated_to_me or [],
        "escalated_to_gandalf": escalated_up or [],
        "learnings": learnings or [],
        "action_items": action_items or [],
    }
    _append_jsonl(MEMORY_FILES["huddle_log"], entry)


# ─────────────────────────────────────────────
# HEALTH STATE
# ─────────────────────────────────────────────

def update_health_state(updates: dict):
    """Update the health state JSON file with new values."""
    path = MEMORY_FILES["health_state"]
    current = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}

    current["last_updated"] = _now()
    current.update(updates)

    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    logger.info(f"Updated health_state.json: {list(updates.keys())}")


# ─────────────────────────────────────────────
# RUN LOG (vault)
# ─────────────────────────────────────────────

def log_run(mode: str, duration_seconds: float, outcome: str, notes: str = ""):
    """Append a run entry to RUN-LOG.md in the vault."""
    run_log_path = VAULT_DIR / "RUN-LOG.md"
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"| {date} | {mode} | {duration_seconds:.1f}s | {outcome} | {notes} |"
    _append_md(run_log_path, entry)


# ─────────────────────────────────────────────
# LEARNING LOG (vault)
# ─────────────────────────────────────────────

def log_learning(pattern: str, evidence: str, recommendation: str):
    """Add a distilled learning to LEARNING-LOG.md."""
    learning_path = VAULT_DIR / "LEARNING-LOG.md"
    date = datetime.now().strftime("%Y-%m-%d")
    entry = f"""### [{date}] {pattern}
**Evidence:** {evidence}
**Recommendation:** {recommendation}
"""
    _append_md(learning_path, entry)


# ─────────────────────────────────────────────
# TEAM COACHING (write to other agents' LEARNING-LOG)
# ─────────────────────────────────────────────

def coach_agent(agent_name: str, pattern: str, evidence: str, recommendation: str):
    """
    Write a learning to another agent's LEARNING-LOG.md.
    Kennedy can only coach Baggins and Oden.
    """
    allowed = ["baggins", "oden"]
    if agent_name.lower() not in allowed:
        logger.warning(f"Cannot coach {agent_name} — only {allowed}")
        return

    learning_path = TR_REPO_PATH / f"agents/{agent_name}/vault/LEARNING-LOG.md"
    if not learning_path.exists():
        logger.warning(f"LEARNING-LOG.md not found for {agent_name}")
        return

    date = datetime.now().strftime("%Y-%m-%d")
    entry = f"""### [{date}] From Kennedy: {pattern}
**Evidence:** {evidence}
**Recommendation:** {recommendation}
"""
    _append_md(learning_path, entry)
    logger.info(f"Coached {agent_name}: {pattern}")


if __name__ == "__main__":
    # Test logging
    logging.basicConfig(level=logging.INFO)
    log_experiment("test123", "3.5%_ctr", "keep", "Test experiment", "x", "benchmark")
    log_reflection(
        hypothesis="Testing logger",
        action="Ran test",
        outcome="Logger works",
        why="Because we tested it",
        next_step="Deploy"
    )
    update_health_state({"status": "healthy", "test": True})
    print("All logging functions tested successfully.")
