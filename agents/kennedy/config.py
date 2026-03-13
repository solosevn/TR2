"""
Kennedy — Media Director Configuration
=======================================
Loads secrets from .env, defines all constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from agent directory
load_dotenv(Path(__file__).parent / ".env")

# ──────────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────────
KENNEDY_BOT_TOKEN = os.getenv("KENNEDY_BOT_TOKEN", "")
DAVID_CHAT_ID = int(os.getenv("DAVID_CHAT_ID", "0"))

# ──────────────────────────────────────────────────────────
# GROK (xAI) — OpenAI-compatible API
# ──────────────────────────────────────────────────────────
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
GROK_API_BASE = "https://api.x.ai/v1"
GROK_MODEL = "grok-4"              # Strategy: huddles, experiments, self-improvement
GROK_FAST_MODEL = "grok-4.1-fast"  # Operations: posting, measurement, routine decisions

# ──────────────────────────────────────────────────────────
# GITHUB
# ──────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_OWNER = "solosevn"
REPO_NAME = "TR2"
REPO_BRANCH = "main"
GITHUB_API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"

# ──────────────────────────────────────────────────────────
# PLATFORM APIs
# ──────────────────────────────────────────────────────────
# X/Twitter (Free Tier)
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET", "")

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = "Kennedy Media Agent v1.0 by /u/trainingrun"
TARGET_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "LocalLLaMA",
    "singularity",
]

# YouTube Data API v3
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")

# LinkedIn
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")

# Google Analytics 4
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
GA_PROPERTY_ID = os.getenv("GA_PROPERTY_ID", "")

# ──────────────────────────────────────────────────────────
# PATHS — Local repo on David's Mac
# ──────────────────────────────────────────────────────────
TR_REPO_PATH = Path(os.getenv("TR_REPO_PATH", str(Path.home() / "Desktop" / "TR2")))
SCOUT_BRIEFING_PATH = TR_REPO_PATH / "scout-briefing.json"
AGENT_DIR = Path(__file__).parent
VAULT_DIR = AGENT_DIR / "vault"
MEMORY_DIR = AGENT_DIR / "memory"
SKILLS_DIR = AGENT_DIR / "skills"
LOG_FILE = AGENT_DIR / "kennedy.log"

# Ensure directories exist
MEMORY_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────
# CONTEXT VAULT — Files the agent reads for instructions
# ──────────────────────────────────────────────────────────
VAULT_FILES = {
    "user_md": "shared/USER.md",
    "reasoning_md": "shared/REASONING-CHECKLIST.md",
    "soul_md": "agents/kennedy/vault/SOUL.md",
    "config_md": "agents/kennedy/vault/CONFIG.md",
    "process_md": "agents/kennedy/vault/PROCESS.md",
    "cadence_md": "agents/kennedy/vault/CADENCE.md",
    "run_log_md": "agents/kennedy/vault/RUN-LOG.md",
    "learning_md": "agents/kennedy/vault/LEARNING-LOG.md",
    "style_md": "agents/kennedy/vault/STYLE-EVOLUTION.md",
    "loop_md": "agents/kennedy/vault/LOOP.md",
    "memory_md": "agents/kennedy/vault/MEMORY-PROTOCOL.md",
    "autonomy_md": "agents/kennedy/vault/AUTONOMY-RULES.md",
}

# ──────────────────────────────────────────────────────────
# MEMORY FILES — Runtime state
# ──────────────────────────────────────────────────────────
MEMORY_FILES = {
    "results_tsv": MEMORY_DIR / "results.tsv",
    "tried_fixes": MEMORY_DIR / "tried_fixes.jsonl",
    "error_log": MEMORY_DIR / "error_log.jsonl",
    "reflection_log": MEMORY_DIR / "reflection_log.jsonl",
    "health_state": MEMORY_DIR / "health_state.json",
    "huddle_log": MEMORY_DIR / "huddle_log.jsonl",
}

# ──────────────────────────────────────────────────────────
# UTM TRACKING
# ──────────────────────────────────────────────────────────
UTM_BASE = {
    "x": "utm_source=x&utm_medium=social",
    "reddit": "utm_source=reddit&utm_medium=social",
    "linkedin": "utm_source=linkedin&utm_medium=social",
    "hackernews": "utm_source=hackernews&utm_medium=social",
    "youtube": "utm_source=youtube&utm_medium=video",
    "newsletter": "utm_source=newsletter&utm_medium=email",
}

# ──────────────────────────────────────────────────────────
# TIMING
# ──────────────────────────────────────────────────────────
ACTIVE_HOURS_START = 6   # 6:00 AM CST
ACTIVE_HOURS_END = 21    # 9:00 PM CST (21:30 for reflection)
HEARTBEAT_INTERVAL = 1800  # 30 minutes in seconds
APPROVAL_TIMEOUT_MINUTES = 120
CYCLE_TIMEOUT_MINUTES = 30
MEASUREMENT_TIMEOUT_MINUTES = 15
SELF_IMPROVEMENT_TIMEOUT_MINUTES = 120
MAX_SELF_IMPROVEMENT_PER_WEEK = 3

# ──────────────────────────────────────────────────────────
# SITES — URLs for UTM link generation
# ──────────────────────────────────────────────────────────
TRAININGRUN_URL = "https://trainingrun.ai"
TSARENA_URL = "https://tsarena.ai"
NEWS_URL = f"{TRAININGRUN_URL}/TR2/news.html"
LEADERBOARD_URL = f"{TRAININGRUN_URL}/TR2/index.html"
