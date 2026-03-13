"""
Kennedy — Context Loader
=========================
Boot sequence: loads vault files + memory files into a context dict
that gets injected into Grok API calls as system context.

Read before acting. This is the V1 → TR2 fix.
"""

import json
import logging
from pathlib import Path
from config import (
    VAULT_FILES, MEMORY_FILES, GITHUB_TOKEN, GITHUB_RAW_BASE,
    VAULT_DIR, MEMORY_DIR, TR_REPO_PATH
)

logger = logging.getLogger("kennedy.context_loader")


def load_vault_file(key: str, repo_path: str) -> str:
    """Load a vault file from local repo or GitHub raw."""
    local_path = TR_REPO_PATH / repo_path
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")

    # Fallback: try GitHub raw URL
    if GITHUB_TOKEN:
        import requests
        url = f"{GITHUB_RAW_BASE}/{repo_path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.warning(f"Failed to fetch {repo_path} from GitHub: {e}")

    logger.warning(f"Vault file not found: {repo_path}")
    return ""


def load_memory_file(key: str, path: Path, last_n: int = None) -> str:
    """Load a memory file. For JSONL files, optionally load only last N entries."""
    if not path.exists():
        return ""

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return ""

    # For JSONL files, optionally return only last N entries
    if last_n and path.suffix == ".jsonl":
        lines = content.strip().split("\n")
        lines = [l for l in lines if l.strip()]  # Remove empty lines
        return "\n".join(lines[-last_n:])

    # For TSV files, optionally return header + last N entries
    if last_n and path.suffix == ".tsv":
        lines = content.strip().split("\n")
        if len(lines) <= 1:
            return content  # Header only
        header = lines[0]
        data_lines = lines[1:]
        return header + "\n" + "\n".join(data_lines[-last_n:])

    return content


def load_health_state() -> dict:
    """Load the current health state as a dict."""
    path = MEMORY_FILES["health_state"]
    if not path.exists():
        return {"status": "initializing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse health_state.json: {e}")
        return {"status": "error", "parse_error": str(e)}


def load_full_context() -> dict:
    """
    Load all vault and memory files into a context dict.
    This is called at every boot cycle.

    Returns:
        dict with keys:
            - vault: dict of vault file contents
            - memory: dict of memory file contents
            - health: current health state dict
            - brain: brain.md contents
    """
    context = {
        "vault": {},
        "memory": {},
        "health": {},
        "brain": "",
    }

    # Load vault files
    for key, repo_path in VAULT_FILES.items():
        content = load_vault_file(key, repo_path)
        if content:
            context["vault"][key] = content
            logger.info(f"Loaded vault: {key} ({len(content)} chars)")
        else:
            logger.warning(f"Empty vault: {key}")

    # Load memory files with limits
    memory_limits = {
        "results_tsv": 20,       # Last 20 experiments
        "tried_fixes": 50,       # Last 50 fix attempts
        "reflection_log": 10,    # Last 10 reflections
        "error_log": 20,         # Last 20 errors
        "huddle_log": 3,         # Last 3 huddles
    }

    for key, path in MEMORY_FILES.items():
        if key == "health_state":
            continue  # Loaded separately
        last_n = memory_limits.get(key)
        content = load_memory_file(key, path, last_n=last_n)
        context["memory"][key] = content
        if content:
            logger.info(f"Loaded memory: {key} ({len(content)} chars)")

    # Load health state
    context["health"] = load_health_state()

    # Load brain.md
    brain_path = Path(__file__).parent / "brain.md"
    if brain_path.exists():
        context["brain"] = brain_path.read_text(encoding="utf-8")
        logger.info(f"Loaded brain.md ({len(context['brain'])} chars)")

    # Load Gollum's scout briefing if available
    from config import SCOUT_BRIEFING_PATH
    if SCOUT_BRIEFING_PATH.exists():
        try:
            briefing = json.loads(SCOUT_BRIEFING_PATH.read_text(encoding="utf-8"))
            context["scout_briefing"] = briefing
            logger.info("Loaded scout-briefing.json")
        except Exception as e:
            logger.warning(f"Failed to load scout-briefing.json: {e}")

    return context


def build_system_prompt(context: dict, mode: str = "strategy") -> str:
    """
    Build a system prompt for Grok API calls from loaded context.

    Args:
        context: The full context dict from load_full_context()
        mode: "strategy" (Grok 4) or "operations" (Grok 4.1 Fast)

    Returns:
        System prompt string
    """
    parts = []

    # Brain is always included
    if context.get("brain"):
        parts.append(context["brain"])

    # For strategy calls, include more context
    if mode == "strategy":
        # Include SOUL and key vault files
        for key in ["soul_md", "loop_md", "autonomy_md", "learning_md"]:
            if key in context["vault"]:
                parts.append(f"\n---\n## {key}\n{context['vault'][key]}")

        # Include recent experiments
        if context["memory"].get("results_tsv"):
            parts.append(f"\n---\n## Recent Experiments\n```\n{context['memory']['results_tsv']}\n```")

        # Include recent reflections
        if context["memory"].get("reflection_log"):
            parts.append(f"\n---\n## Recent Reflections\n{context['memory']['reflection_log']}")

    # For operations, keep it lean
    elif mode == "operations":
        if context["memory"].get("results_tsv"):
            parts.append(f"\n---\n## Recent Results\n```\n{context['memory']['results_tsv']}\n```")

    # Always include health state
    if context.get("health"):
        parts.append(f"\n---\n## Current Health State\n```json\n{json.dumps(context['health'], indent=2)}\n```")

    # Include scout briefing if available
    if context.get("scout_briefing"):
        briefing_summary = json.dumps(context["scout_briefing"], indent=2)[:2000]  # Truncate if huge
        parts.append(f"\n---\n## Today's Intelligence (Gollum)\n```json\n{briefing_summary}\n```")

    return "\n".join(parts)


if __name__ == "__main__":
    # Test context loading
    logging.basicConfig(level=logging.INFO)
    ctx = load_full_context()
    print(f"Vault files loaded: {len(ctx['vault'])}")
    print(f"Memory files loaded: {len(ctx['memory'])}")
    print(f"Health state: {ctx['health'].get('status', 'unknown')}")
    print(f"Brain loaded: {'yes' if ctx['brain'] else 'no'}")
    print(f"Scout briefing: {'yes' if ctx.get('scout_briefing') else 'no'}")
