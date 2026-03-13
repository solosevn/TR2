# Content Scout — CONFIG.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: agents/gollum/vault/

---

## Runtime Environment

| Key | Value |
|-----|-------|
| Python | 3.13 (`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`) |
| Host | David's Mac (local) |
| Service | launchd (`com.trainingrun.scout`) |
| Working Dir | `/Users/davidsolomon/Desktop/TR2/agents/gollum/` |
| Repo Path | `/Users/davidsolomon/Desktop/TR2` |

---

## Models

| Model | Provider | Purpose | Cost |
|-------|----------|---------|------|
| llama3.1:8b | Ollama (local) | Primary brief generation + AI verification Layer 4a | Free |
| grok-3-mini | xAI API | Secondary AI verification Layer 4b | Free tier |

### Ollama Config
- URL: `http://localhost:11434/api/generate`
- Model: `llama3.1:8b`
- Fallback: Skip briefing narrative if Ollama down (still send bullet list)

### xAI Config
- URL: `https://api.x.ai/v1/chat/completions`
- Model: `grok-3-mini`
- API Key: Environment variable `XAI_API_KEY`
- Fallback: Mark items as UNVERIFIED if xAI unavailable

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_TOKEN` | Bot token for @TRnewzBot |
| `TELEGRAM_CHAT_ID` | David's chat ID |
| `XAI_API_KEY` | xAI API key for Grok-3-Mini |
| `TR_REPO_PATH` | Path to trainingrun-site repo |
| `PATH` | System PATH including Python 3.13 |

---

## File Paths

| File | Path | Purpose |
|------|------|---------|
| scout.py | `agents/gollum/scout.py` | Main agent code |
| scout_brain.md | `agents/gollum/scout_brain.md` | Legacy brain file (replaced by vault) |
| scout_context_loader.py | `agents/gollum/scout_context_loader.py` | Vault file loader |
| scout_learning_logger.py | `agents/gollum/scout_learning_logger.py` | Learning/logging system |
| scout-data.json | `agents/gollum/scout-data.json` | Local data store (pruned after 3 days) |
| scout-briefing.json | `$TR_REPO_PATH/scout-briefing.json` | Output for Daily News Agent + website |
| scout-feedback.json | `$TR_REPO_PATH/scout-feedback.json` | Feedback from Daily News Agent |
| scout.log | `agents/gollum/scout.log` | stdout/stderr via launchd |

---

## Vault Files (Read Before Every Cycle)

| Key | GitHub Path |
|-----|-------------|
| SOUL | `agents/gollum/vault/SOUL.md` |
| CONFIG | `agents/gollum/vault/CONFIG.md` |
| PROCESS | `agents/gollum/vault/PROCESS.md` |
| CADENCE | `agents/gollum/vault/CADENCE.md` |
| RUN_LOG | `agents/gollum/vault/RUN-LOG.md` |
| LEARNING_LOG | `agents/gollum/vault/LEARNING-LOG.md` |
| STYLE_EVOLUTION | `agents/gollum/vault/STYLE-EVOLUTION.md` |
| SOURCES | `agents/gollum/vault/SOURCES.md` |
| TRUTH_FILTER | `agents/gollum/vault/TRUTH-FILTER.md` |

---

## Telegram Config

| Key | Value |
|-----|-------|
| Bot | @TRnewzBot |
| Chat ID | David's personal chat |
| Max message length | 3900 chars (auto-split) |
| Morning brief | 5:30 AM CST |
| Status updates | Every 4 hours during scrape window |

---

## Scheduling

| Parameter | Value |
|-----------|-------|
| Scrape window | 7:30 AM - 11:00 PM CST |
| Scrape interval | Every 30 minutes |
| Brief generation | 5:30 AM CST |
| Data pruning | Items older than 3 days removed |
| Staleness filter | >3 days deprioritize, >7 days drop |

---

## Request Config

| Parameter | Value |
|-----------|-------|
| Timeout | 20 seconds |
| User-Agent | `ContentScout/1.2 (trainingrun.ai research/educational AI news aggregator)` |
| Reddit delay | 2 seconds between subreddit calls |
| Ethical check | Only scrape known public domains |

---

## Source Weight System

- Default weight: 1.0x for all sources
- Range: 0.5x (deprioritized) to 2.0x (boosted)
- Applied during RANKING, not during scraping (still scrape everything)
- Weights read from STYLE-EVOLUTION.md before each briefing
- Updated by scout_learning_logger.py based on feedback from Daily News Agent

---

*Read by Content Scout via scout_context_loader.py at startup and before each cycle.*
