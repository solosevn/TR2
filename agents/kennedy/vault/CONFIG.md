# CONFIG — Kennedy, Media Director

> **Version:** 1.0 — March 13, 2026
> **Updated by:** David + Claude

---

## Model Configuration

| Setting | Value |
|---|---|
| **Primary Model (Strategy)** | Grok 4 via xAI API |
| **Fast Model (Operations)** | Grok 4.1 Fast via xAI API |
| **API Base** | https://api.x.ai/v1 |
| **API Key** | Loaded from `.env` → `XAI_API_KEY` |
| **Fallback Model** | Claude Haiku 4.5 (Anthropic API) if xAI rate-limited |

### When to use which model

- **Grok 4:** Daily huddle reasoning, content strategy decisions, experiment analysis, self-improvement code reviews, weekly media strategy
- **Grok 4.1 Fast:** Routine posting decisions, content formatting, measurement reads, UTM generation, platform API calls, status checks

### Cost control

- Target: ~30-35 API calls/day total
- Grok 4: ~3 calls/day (strategy only)
- Grok 4.1 Fast: ~25-30 calls/day (operations)
- Estimated monthly cost: $3-5/month
- If approaching rate limits, switch to Grok 4.1 Fast for all calls

---

## Telegram Configuration

| Setting | Value |
|---|---|
| **Bot Name** | Kennedy |
| **Bot Username** | @KennedyMBot |
| **Bot Token** | Loaded from `.env` → `KENNEDY_BOT_TOKEN` |
| **David's Chat ID** | Loaded from `.env` → `DAVID_CHAT_ID` |

### Telegram commands

- `/status` — Kennedy reports current health, last cycle results, pending content
- `/approve` — Approve pending content for publishing
- `/hold` — Hold all publishing (emergency stop)
- `/strategy` — Request current content strategy summary
- `/experiments` — Show last 10 experiment results from results.tsv
- `HALT` — Emergency stop all operations including self-improvement

---

## GitHub Configuration

| Setting | Value |
|---|---|
| **Token** | Loaded from `.env` → `GITHUB_TOKEN` |
| **Repo Owner** | solosevn |
| **Repo Name** | TR2 |
| **Branch** | main (reading/publishing) |
| **Self-improvement branches** | autoresearch/YYMMDD-kennedy (feature branches for L4 code edits) |
| **API Base** | https://api.github.com/repos/solosevn/TR2 |
| **Raw Content Base** | https://raw.githubusercontent.com/solosevn/TR2/main |

### GitHub Traffic API (free)

- `GET /repos/solosevn/TR2/traffic/views`
- `GET /repos/solosevn/TR2/traffic/clones`
- `GET /repos/solosevn/TR2/traffic/popular/referrers`
- `GET /repos/solosevn/TR2/traffic/popular/paths`
- Also monitor: solosevn/trainingrun-site for legacy traffic

---

## Platform API Configuration

### X/Twitter (Free Tier)

| Setting | Value |
|---|---|
| **API Version** | v2 |
| **Auth** | OAuth 2.0 — loaded from `.env` |
| **Post limit** | 1,500 tweets/month |
| **Read limit** | ~1 request per 15 minutes |
| **Read capability** | Public metrics (likes, retweets, replies, quotes) on own tweets |
| **NOT available on free** | Impressions, search |
| **Workaround** | UTM links + Google Analytics for click-through measurement |

### Reddit (Free Tier)

| Setting | Value |
|---|---|
| **API Version** | OAuth2 |
| **Auth** | Client ID + Secret — loaded from `.env` |
| **Rate limit** | 100 requests/minute |
| **Target subreddits** | r/MachineLearning, r/artificial, r/LocalLLaMA, r/singularity |
| **Capability** | Post, read upvotes/comments, track post performance |

### YouTube Data API v3 (Free)

| Setting | Value |
|---|---|
| **API Key** | Loaded from `.env` → `YOUTUBE_API_KEY` |
| **Quota** | 10,000 units/day (free) |
| **Capability** | Read view counts, watch time, CTR, subscriber changes, comments |
| **Channel** | TrainingRun (channel ID in `.env`) |

### LinkedIn (Free Tier)

| Setting | Value |
|---|---|
| **Auth** | OAuth 2.0 — loaded from `.env` |
| **Rate limit** | 100 requests/day per user token |
| **Capability** | Post content. No analytics (enterprise only). |
| **Workaround** | UTM links + Google Analytics for measurement |

### Google Analytics 4 (Free)

| Setting | Value |
|---|---|
| **Property** | TrainingRun.AI + TSArena.AI |
| **Measurement ID** | In `.env` → `GA_MEASUREMENT_ID` |
| **Data API** | Google Analytics Data API v1 (for programmatic reads) |
| **Capability** | Pageviews, sessions, UTM source/medium/campaign, bounce rate, time on page, referrers |

### Hacker News (Free, no auth)

| Setting | Value |
|---|---|
| **API** | Firebase REST API (https://hacker-news.firebaseio.com/v0/) |
| **Capability** | Submit stories, read scores/comments |
| **No auth required** | Public API |

---

## File Paths

| Path | Purpose |
|---|---|
| `agents/kennedy/` | Kennedy's home directory |
| `agents/kennedy/vault/` | Core 10 vault files |
| `agents/kennedy/memory/` | Runtime state (tried_fixes, results.tsv, etc.) |
| `agents/kennedy/skills/` | Reasoning templates |
| `agents/kennedy/.env` | Secrets (in .gitignore, never committed) |
| `agents/kennedy/kennedy.py` | Main agent script |
| `agents/kennedy/brain.md` | System prompt loaded every session |
| `agents/kennedy/config.py` | Python config (loads .env, defines constants) |
| `agents/kennedy/kennedy_context_loader.py` | Boot sequence — loads vault + memory |
| `agents/kennedy/kennedy_learning_logger.py` | Post-action — writes to vault + memory |
| `scout-briefing.json` | Gollum's daily intelligence (repo root) |
| `assets/Kennedy.png` | Kennedy's avatar |
| `shared/USER.md` | David's preferences (shared across agents) |
| `shared/REASONING-CHECKLIST.md` | Shared reasoning template |

---

## Security Notes

- All secrets in `.env` files — NEVER in code or committed to repo
- `.env` is in `.gitignore`
- GitHub token: fine-grained PAT scoped to solosevn/TR2 only
- Self-improvement edits: feature branches only, never push directly to main
- HALT command via Telegram stops all operations immediately
- Kennedy cannot edit files outside `agents/kennedy/` directory
