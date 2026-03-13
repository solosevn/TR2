#!/usr/bin/env python3
"""
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  âï¸  GIMLI â TR2 Unified DDP (Daily Data Pipeline)
  solosevn/TR2 | TR2-unified-v1.3
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  Agent:  Gimli / TRSbench Scoring Engine (L0 â deterministic)
  Role:   ONE scraper, 10 pillars, 37 sources.
          Feeds trs-data-unified.json for the TR2 unified leaderboard.
  Avatar: assets/emojis.com gimli-dwarf.png
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re
from datetime import date, datetime
from pathlib import Path

# ââ dependency guard ââââââââââââââââââââââââââââââââââââââââââââââ
for pkg, hint in [
    ("playwright", "pip3 install playwright && python3 -m playwright install chromium"),
    ("bs4",        "pip3 install beautifulsoup4"),
    ("telegram",   "pip3 install python-telegram-bot"),
    ("requests",   "pip3 install requests"),
]:
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: {hint}")

import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from telegram import Bot

# ââ logging âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("gimli")

# ââ CONFIG ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(__file__).resolve().parent.parent
DATA_FILE   = REPO_PATH / "trs-data-unified.json"
STATUS_FILE = REPO_PATH / "status.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ââ TRSbench Bible V2.5 weights âââââââââââââââââââââââââââââââââââ

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  WEIGHTS â TR2-unified-v1.3
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
WEIGHTS = {
    "safety":               0.16,
    "reasoning":            0.13,
    "truth_confabulation":  0.14,
    "human_preference":     0.11,
    "coding":               0.11,
    "agent_capability":     0.10,
    "knowledge":            0.08,
    "forecasting_finance":  0.07,
    "efficiency":           0.05,
    "usage_adoption":       0.05,
}

PILLAR_ORDER = list(WEIGHTS.keys())
PILLAR_NAMES = {
    "safety":              "Safety",
    "reasoning":           "Reasoning",
    "truth_confabulation": "Truth & Confabulation",
    "human_preference":    "Human Preference",
    "coding":              "Coding",
    "agent_capability":    "Agent Capability",
    "knowledge":           "Knowledge",
    "forecasting_finance": "Forecasting & Finance",
    "efficiency":          "Efficiency",
    "usage_adoption":      "Usage / Adoption",
}

TOTAL_SOURCES = 40
QUALIFICATION_MIN_PILLARS = 1


def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text}")
        return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try:
        asyncio.run(_send())
    except Exception as e:
        log.warning(f"Telegram non-fatal: {e}")


# ââ PLAYWRIGHT HELPERS ââââââââââââââââââââââââââââââââââââââââââââ
# ââ Playwright helpers âââââââââââââââââââââââââââââââââââââââââââ
def playwright_get(url: str, wait_ms: int = 5000) -> str:
    """Launch headless Chromium, load url, return page HTML."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def playwright_get_innertext(url: str, wait_ms: int = 8000) -> str:
    """Load url with Playwright, return body.innerText (for non-table JS pages)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        text = page.evaluate("document.body.innerText") or ""
        browser.close()
    return text


def playwright_get_hfspace(url: str, wait_ms: int = 15000) -> str:
    """Load HuggingFace Space URL; returns inner .hf.space iframe HTML if present."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        for frame in page.frames:
            if "hf.space" in frame.url:
                try:
                    frame.wait_for_load_state("networkidle", timeout=30_000)
                except Exception:
                    pass
                page.wait_for_timeout(5000)
                html = frame.content()
                browser.close()
                return html
        html = page.content()
        browser.close()
    return html


def _parse_helm_leaderboard(url: str, source_name: str, wait_ms: int = 10000) -> dict[str, float]:
    """
    Generic parser for Stanford CRFM HELM leaderboards.
    All HELM leaderboards share the same Vue table structure:
      col0 = model name, col1 = mean score (0.0-1.0 float)
    Returns {model: score_0_to_100}.
    """
    scores: dict[str, float] = {}
    try:
        log.info(f"Scraping {source_name} (HELM)...")
        html = playwright_get(url, wait_ms=wait_ms)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers) if "model" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "mean" in h or "score" in h or "average" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                raw_name = cells[model_col].get_text(strip=True)
                name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
                if not name or len(name) < 2:
                    continue
                score_raw = cells[score_col].get_text(strip=True)
                try:
                    val = float(score_raw)
                    if 0 < val <= 1.0:
                        val = round(val * 100, 4)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â {source_name}: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ {source_name} not available: {e}")
    return scores


# ââ SCRAPERS â SAFETY (21%) âââââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 1: SAFETY (16%) âââââââââââââââââââââââââââââââââââââ
# âââ SHARED HELPERS âââââââââââââââââââââââââââââââââââââââââââ

def parse_first_table(html: str) -> list[dict]:
    """Return rows as list of {col: val} dicts from the largest table."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []
    target = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = target.find_all("tr")
    if len(rows) < 2:
        return []
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    result = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if cells:
            result.append(dict(zip(headers, cells)))
    return result


def _parse_mcp_atlas_innertext(text: str) -> dict[str, float]:
    """Parse MCP Atlas leaderboard innerText."""
    scores: dict[str, float] = {}
    lines_list = [l.strip() for l in text.split("\n") if l.strip()]
    score_pat = re.compile(r"^(\d+(?:\.\d+)?)\s*%$")
    _skip = {"introduction", "key metrics", "release", "paper", "dataset",
             "github", "performance", "top pass", "held-out", "mcp", "atlas",
             "scale", "leaderboard", "benchmark", "tasks", "tools", "servers"}
    for i, line in enumerate(lines_list):
        m = score_pat.match(line)
        if m and i > 0:
            name = lines_list[i - 1]
            if score_pat.match(name):
                continue
            if (len(name) > 2
                    and not any(name.lower().startswith(kw) for kw in _skip)
                    and name not in scores):
                scores[name] = float(m.group(1))
    return scores


def scrape_helm_safety() -> dict[str, float]:
    """HELM Safety leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/safety/latest/#/leaderboard
    Measures: HarmBench, SimpleSafetyTests, BBQ, Anthropic Red Team, XSTest.
    87 models. Higher score = safer. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/safety/latest/#/leaderboard",
        "HELM Safety",
        wait_ms=12000,
    )


def scrape_airbench() -> dict[str, float]:
    """AIR-Bench (Stanford CRFM) â refusal-rate safety leaderboard.
    Source: https://crfm.stanford.edu/helm/air-bench/latest/#/leaderboard
    87 models. Measures compliance with AI safety regulations (refusal rate).
    Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/air-bench/latest/#/leaderboard",
        "AIR-Bench",
        wait_ms=12000,
    )


# ââ SCRAPERS â REASONING (20%) ââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 2: TRUTH & CONFABULATION (14%) ââââââââââââââââââââââ
def scrape_simpleqa() -> dict:
    """
    llm-stats.com/benchmarks/simpleqa
    Returns factuality {model: correct_pct} â how often model answers correctly.
    """
    factuality: dict = {}
    try:
        log.info("Scraping SimpleQA (truthfulness)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://llm-stats.com/benchmarks/simpleqa",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                return trs.map(r => {
                    const cells = r.querySelectorAll('td');
                    if (cells.length < 4) return null;
                    const nameEl = cells[1].querySelector('a') || cells[1];
                    const name = nameEl.textContent.trim().split('\\n')[0].trim();
                    const correct = parseFloat(cells[2].textContent.trim());
                    if (!name || isNaN(correct)) return null;
                    return {name, correct};
                }).filter(Boolean);
            }""")
            browser.close()

        for row in rows:
            name = row.get("name", "")
            correct = row.get("correct")
            if name and correct is not None:
                pct = round(correct * 100, 2) if correct <= 1.0 else round(correct, 2)
                if 0 < pct <= 100:
                    factuality[name] = pct

        log.info(f"  â SimpleQA: {len(factuality)} models")
    except Exception as e:
        log.warning(f"  â ï¸ SimpleQA: {e}")
    return factuality


# ââ 2: FACTS Benchmark â Truthfulness ââââââââââââââââââââââââââââ
def scrape_facts() -> dict:
    """
    FACTS Benchmark Suite (Google DeepMind) â kaggle.com/benchmarks/google/facts
    4 sub-benchmarks: Parametric, Search, Multimodal, Grounding.
    Uses the overall Average score. Higher = more factually accurate.
    Last updated December 6, 2025. 15+ frontier models.
    Returns {model: average_score (0-100)}
    NOTE: Kaggle renders as a React SPA with no <table> elements in headless mode.
    Uses innerText name-then-scores extraction. KNOWN_VALUES always supplement.
    """
    scores: dict = {}
    # Last-known published values (December 6, 2025) â always used as supplement
    KNOWN_VALUES = {
        "Gemini 3 Pro Preview":         68.8,
        "Gemini 2.5 Pro":               62.1,
        "GPT-5":                        61.8,
        "Grok 4":                       53.6,
        "o3":                           52.0,
        "Claude Opus 4.5":              51.3,
        "GPT-4.1":                      50.5,
        "Gemini 2.5 Flash":             50.4,
        "GPT-5.1":                      49.4,
        "Claude Sonnet 4.5 (thinking)": 47.9,
        "Claude Opus 4.1":              46.5,
        "GPT-5 mini":                   45.9,
        "Claude Sonnet 4":              42.8,
        "o4 mini":                      37.6,
        "Grok 4 Fast Reasoning":        36.0,
    }
    try:
        log.info("Scraping FACTS Benchmark (Kaggle)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://www.kaggle.com/benchmarks/google/facts",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            # Kaggle is a React SPA â no <table> elements; wait for JS render
            page.wait_for_timeout(8000)

            rows = page.evaluate("""() => {
                // Kaggle FACTS renders as flex/grid, not <table>.
                // Model names and scores appear in innerText as two separate
                // sequential blocks: all N names first, then all N avg scores.
                // Strategy: extract names (follow rank integers), then pair
                // with the first percentage of each model's score block.
                const HEADERS = ['#','Model','Average','Grounding Score','info',
                                  'Multimodal Score','Search Score','Parametric Score'];
                const text = document.body.innerText;
                const start = text.indexOf('#\\nModel');
                if (start === -1) return [];
                const section = text.substring(start, start + 8000);
                const lines = section.split('\\n').map(l => l.trim()).filter(l => l);
                const names = [];
                const avgs  = [];
                let inNames = true;
                let prevWasRank = false;
                for (let i = 0; i < lines.length; i++) {
                    const l = lines[i];
                    if (HEADERS.includes(l)) continue;
                    if (/^\\d+$/.test(l)) { prevWasRank = true; continue; }
                    if (prevWasRank && inNames && !/^\\d+\\.\\d%$/.test(l) && !/^Â±/.test(l)) {
                        names.push(l);
                        prevWasRank = false;
                        continue;
                    }
                    prevWasRank = false;
                    if (/^\\d{1,3}\\.\\d%$/.test(l)) {
                        inNames = false;
                        avgs.push(parseFloat(l));
                        i += 8;  // skip 4 sub-scores + 4 Â±margins
                    }
                }
                return names.slice(0, avgs.length).map((n, idx) => ({name: n, avg: avgs[idx]}));
            }""")
            browser.close()

        for row in rows:
            name = row.get("name", "").strip()
            avg  = row.get("avg")
            if name and avg is not None and 0 < avg <= 100:
                scores[name] = round(avg, 2)

        live_count = len(scores)
        # Always supplement with KNOWN_VALUES for models not captured live
        for model, avg in KNOWN_VALUES.items():
            if model not in scores:
                scores[model] = avg

        if live_count == 0:
            log.info(f"  FACTS: 0 scraped â using {len(scores)} known values")
        else:
            log.info(f"  â FACTS: {len(scores)} models ({live_count} live + {len(scores)-live_count} known)")
    except Exception as e:
        log.warning(f"  â ï¸ FACTS: {e} â using known values")
        scores = {**KNOWN_VALUES, **scores}
    return scores


# ââ 3: TruthfulQA âââââââââââââââââââââââââââââââââââââââââââââââââ
def scrape_truthfulqa() -> dict:
    """
    llm-stats.com/benchmarks/truthfulqa
    MC1 + MC2 scores (0-100). Returns average of available sub-scores.
    Tests whether models avoid well-known misconceptions and plausible falsehoods.
    """
    scores: dict = {}
    try:
        log.info("Scraping TruthfulQA...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://llm-stats.com/benchmarks/truthfulqa",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                return trs.map(r => {
                    const cells = r.querySelectorAll('td');
                    if (cells.length < 3) return null;
                    const nameEl = cells[1].querySelector('a') || cells[1];
                    const name = nameEl.textContent.trim().split('\\n')[0].trim();
                    const mc1 = parseFloat(cells[2].textContent.trim());
                    const mc2 = cells[3] ? parseFloat(cells[3].textContent.trim()) : NaN;
                    if (!name) return null;
                    return {name, mc1, mc2};
                }).filter(Boolean);
            }""")
            browser.close()

        def clean_tqa_name(raw: str) -> str:
            n = raw.strip().split('\n')[0].strip()
            if '/' in n:
                n = n.split('/')[-1]
            for pfx in ['meta-', 'google-', 'openai-', 'anthropic-', 'mistralai-',
                        'deepseek-ai-', 'Qwen-', 'microsoft-', 'nvidia-']:
                if n.lower().startswith(pfx.lower()):
                    n = n[len(pfx):]
            return n.strip()

        for row in rows:
            name = row.get("name", "")
            mc1  = row.get("mc1")
            mc2  = row.get("mc2")
            if not name:
                continue
            name = clean_tqa_name(name)
            if not name or len(name) < 2:
                continue
            values = []
            for v in [mc1, mc2]:
                if v is not None and not (isinstance(v, float) and (v != v)):
                    pct = round(v * 100, 2) if v <= 1.0 else round(v, 2)
                    if 0 < pct <= 100:
                        values.append(pct)
            if values:
                scores[name] = round(sum(values) / len(values), 2)

        log.info(f"  â TruthfulQA: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ TruthfulQA: {e}")
    return scores


# ââ 4: HalluHard â Hallucination âââââââââââââââââââââââââââââââââ
def scrape_halluhard() -> dict:
    """
    HalluHard â halluhard.com (EPFL-backed)
    Multi-turn hallucination benchmark across 4 domains:
    Legal Cases, Research Questions, Medical Guidelines, Coding.
    Score = Hallucination Rate (lower is better). INVERTED during normalization.
    Filters -Web-Search variants so only base model scores are used.
    Returns {model: hallucination_rate (0-100)}
    """
    scores: dict = {}
    # Last-known published values (March 2026) as fallback
    # NOTE: names must match roster format (spaces, not hyphens)
    KNOWN_VALUES = {
        "GPT-5.2":           58.8,
        "Gemini 3.1 Pro":    57.1,
        "Claude Opus 4.5":   60.0,
        "Claude Opus 4.6":   60.9,
        "Gemini 3 Pro":      61.9,
        "Claude Sonnet 4.6": 63.7,
        "GPT-5 thinking":    64.8,
        "Claude Sonnet 4.5": 65.6,
        "Gemini 3 Flash":    69.5,
        "GPT-5":             71.8,
        "Grok 4":            75.3,
        "GPT-5 mini":        75.9,
        "Claude Haiku 4.5":  79.6,
    }
    try:
        log.info("Scraping HalluHard (hallucination rate)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://halluhard.com/",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                # Wait for the bar chart leaderboard to render
                page.wait_for_selector(
                    "[class*='leaderboard'], [class*='rank'], table, [class*='bar']",
                    timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(6000)

            rows = page.evaluate("""() => {
                const results = [];

                // Strategy 1: standard <table>
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                for (const tr of trs) {
                    const cells = tr.querySelectorAll('td');
                    if (cells.length < 2) continue;
                    const name = (cells[0].textContent || '').trim() ||
                                 (cells[1] ? cells[1].textContent.trim() : '');
                    for (let i = 1; i < cells.length; i++) {
                        const v = parseFloat(cells[i].textContent.trim());
                        if (!isNaN(v) && v > 0 && v <= 100) {
                            results.push({name: name.trim(), rate: v});
                            break;
                        }
                    }
                }
                if (results.length >= 5) return results;

                // Strategy 2: parse inner-text line by line
                // HalluHard renders as: Rank | ModelName | Score | [domain scores]
                const allText = document.body.innerText;
                const lines = allText.split('\\n').map(l => l.trim()).filter(l => l);
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    // A score line is a standalone decimal like "30.2" or "60.9"
                    if (/^\\d{1,2}\\.\\d$/.test(line)) {
                        const rate = parseFloat(line);
                        if (rate > 0 && rate <= 100) {
                            // Model name is on the line before the score
                            for (let j = i - 1; j >= Math.max(0, i - 4); j--) {
                                const candidate = lines[j];
                                if (candidate && candidate.length >= 3 &&
                                    !/^\\d+$/.test(candidate) &&
                                    !/^(Domain|Turn|All|Average|DOMAIN|TURN|Overview)/i.test(candidate) &&
                                    candidate.length <= 80) {
                                    results.push({name: candidate, rate});
                                    break;
                                }
                            }
                        }
                    }
                }
                return results;
            }""")
            browser.close()

        # Deduplicate: skip Web-Search variants, keep lowest rate per model
        _SKIP_TOKENS = ["web-search", "websearch", "web search"]
        raw: dict = {}
        for row in rows:
            name = row.get("name", "").strip()
            rate = row.get("rate")
            if not name or rate is None or not (0 < rate <= 100):
                continue
            if any(tok in name.lower() for tok in _SKIP_TOKENS):
                log.debug(f"  HalluHard: skipping web-search variant '{name}'")
                continue
            # Keep lowest (best) hallucination rate if duplicate
            if name not in raw or rate < raw[name]:
                raw[name] = round(rate, 2)
        scores = raw

        # Always supplement with KNOWN_VALUES for any model not captured live
        live_count = len(scores)
        for model, rate in KNOWN_VALUES.items():
            if model not in scores:
                scores[model] = rate

        if live_count == 0:
            log.info(f"  HalluHard: 0 scraped â using {len(scores)} known values")
        else:
            log.info(f"  â HalluHard: {len(scores)} models ({live_count} live + {len(scores)-live_count} known)")
    except Exception as e:
        log.warning(f"  â ï¸ HalluHard: {e} â using known values")
        if not scores:
            scores = KNOWN_VALUES.copy()
    return scores


# ââ 5: Vectara Hallucination ââââââââââââââââââââââââââââââââââââââ
def scrape_vectara_hallucination() -> dict:
    """
    huggingface.co/spaces/vectara/leaderboard
    HHEM-2.3: % hallucination in summarization across 7,700+ articles.
    INVERTED during normalization (lower rate = better score).
    130+ models. Updated continuously.
    """
    scores: dict = {}
    try:
        log.info("Scraping Vectara Hallucination (inverted)...")
        html = playwright_get_hfspace(
            "https://huggingface.co/spaces/vectara/leaderboard", wait_ms=15000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    rate = float(clean)
                    if 0 <= rate <= 100:
                        scores[name] = rate
                        break
                except ValueError:
                    pass
        log.info(f"  â Vectara: {len(scores)} models (raw halluc rates)")
    except Exception as e:
        log.warning(f"  â ï¸ Vectara: {e}")
    return scores


# ââ 6: HLE â Reasoning âââââââââââââââââââââââââââââââââââââââââââ
# âââ PILLAR 3: REASONING (13%) ââââââââââââââââââââââââââââââââââ
def scrape_arc_agi2() -> dict[str, float]:
    """arcprize.org/leaderboard â ARC-AGI-2 column. Returns {model: score_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping ARC-AGI-2 (reasoning)...")
        url = "https://arcprize.org/leaderboard"
        html = playwright_get(url, wait_ms=10000)
        rows = parse_first_table(html)
        for row in rows:
            raw_name = row.get("AI System", "")
            if not raw_name:
                vals = list(row.values())
                raw_name = vals[0] if vals else ""
            if not raw_name:
                continue
            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            name = re.sub(r'\s*[Â²Â³Â¹â´âµ]\s*$', '', name).strip()
            arc2_raw = row.get("ARC-AGI-2", "")
            if not arc2_raw:
                continue
            clean = arc2_raw.replace("%", "").strip()
            try:
                pct = float(clean)
                if 0 <= pct <= 100:
                    if name not in scores or pct > scores[name]:
                        scores[name] = pct
            except ValueError:
                pass
        log.info(f"  â ARC-AGI-2: {len(scores)} models")
    except Exception as e:
        log.error(f"  â ARC-AGI-2: {e}")
    return scores


def scrape_livebench_reasoning() -> dict[str, float]:
    """LiveBench â contamination-free reasoning subcategory.
    Source: https://livebench.ai
    55+ models. Uses 'Reasoning Average' column (0-100). Returns {model: score}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping LiveBench Reasoning...")
        html = playwright_get("https://livebench.ai", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 0)
            # Prefer "reasoning average"; fall back to "global average"
            reason_col = next((i for i, h in enumerate(headers)
                               if "reasoning" in h), None)
            if reason_col is None:
                reason_col = next((i for i, h in enumerate(headers)
                                   if "global" in h or "average" in h or "score" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, reason_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[reason_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â LiveBench Reasoning: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ LiveBench Reasoning not available: {e}")
    return scores


def scrape_helm_capabilities() -> dict[str, float]:
    """HELM Capabilities leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/capabilities/latest/#/leaderboard
    68 models. Broad capability benchmark. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/capabilities/latest/#/leaderboard",
        "HELM Capabilities",
        wait_ms=12000,
    )


# ââ SCRAPERS â CODING (20%) âââââââââââââââââââââââââââââââââââââââ


def scrape_hle() -> dict:
    """
    Humanity's Last Exam (HLE) â lastexam.ai
    2,500 expert-level questions across 100+ subjects. Published in Nature 2026.
    Metric: Accuracy (%) â how often model answers expert questions correctly.
    Returns {model: accuracy_pct (0-100)}
    """
    scores: dict = {}
    # Last-known published values (April 2025 dataset update) as fallback
    KNOWN_VALUES = {
        "Gemini 3 Pro":      38.3,
        "GPT-5":             25.3,
        "Grok 4":            24.5,
        "Gemini 2.5 Pro":    21.6,
        "GPT-5-mini":        19.4,
        "Claude Sonnet 4.5": 13.7,
        "Gemini 2.5 Flash":  12.1,
        "DeepSeek-R1":        8.5,
        "o1":                 8.0,
        "GPT-4o":             2.7,
    }
    try:
        log.info("Scraping HLE (Humanity's Last Exam)...")
        _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")

        # Strategy 1: plain requests â table may be in static HTML
        try:
            r = requests.get("https://lastexam.ai/", headers={
                "User-Agent": _ua, "Accept": "text/html,*/*"
            }, timeout=20)
            if r.ok and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, "html.parser")
                for table in soup.find_all("table"):
                    rows_html = table.find_all("tr")
                    if len(rows_html) < 3:
                        continue
                    hdrs = [th.get_text(strip=True).lower()
                            for th in rows_html[0].find_all(["th", "td"])]
                    acc_col = next((i for i, h in enumerate(hdrs)
                                    if "accuracy" in h), None)
                    if acc_col is None:
                        acc_col = 1  # default: 2nd column
                    for row in rows_html[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) <= acc_col:
                            continue
                        name = cells[0].get_text(strip=True)
                        if not name or name.lower() in ("model", "#", "rank"):
                            continue
                        try:
                            v = float(cells[acc_col].get_text(strip=True)
                                      .replace("%", "").strip())
                            if 0 <= v <= 100:
                                scores[name] = round(v, 2)
                        except ValueError:
                            pass
                if scores:
                    log.info(f"  HLE: {len(scores)} via requests+BS4")
        except Exception as e:
            log.debug(f"  HLE requests: {e}")

        # Strategy 2: Playwright â SPA may need JS render
        if not scores:
            log.info("  HLE: trying Playwright...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=_ua)
                page = ctx.new_page()
                try:
                    page.goto("https://lastexam.ai/",
                              wait_until="networkidle", timeout=60_000)
                except Exception:
                    pass
                page.wait_for_timeout(6000)
                rows_js = page.evaluate("""() => {
                    // Look for the results table: Model | Accuracy (%) | CalibError (%)
                    const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                    const results = [];
                    for (const tr of trs) {
                        const cells = tr.querySelectorAll('td');
                        if (cells.length < 2) continue;
                        const name = cells[0].textContent.trim();
                        if (!name || name.length < 2) continue;
                        // First numeric column is accuracy
                        for (let i = 1; i < cells.length; i++) {
                            const v = parseFloat(
                                cells[i].textContent.trim().replace('%',''));
                            if (!isNaN(v) && v >= 0 && v <= 100) {
                                results.push({name, acc: v});
                                break;
                            }
                        }
                    }
                    return results;
                }""")
                browser.close()
                for row in rows_js:
                    name = row.get("name", "").strip()
                    acc  = row.get("acc")
                    if name and acc is not None and 0 <= acc <= 100:
                        scores[name] = round(acc, 2)
                if scores:
                    log.info(f"  HLE: {len(scores)} via Playwright")

        # Last resort: published values
        if not scores:
            log.info("  HLE: using last-known published values (Apr 2025)")
            scores = KNOWN_VALUES.copy()

        log.info(f"  â HLE: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ HLE: {e} â using known values")
        if not scores:
            scores = KNOWN_VALUES.copy()
    return scores


# ââ 7: LiveBench â Reasoning ââââââââââââââââââââââââââââââââââââââ
# âââ PILLAR 4: HUMAN PREFERENCE (11%) âââââââââââââââââââââââââââ
def scrape_arena_overall() -> dict[str, float]:
    """arena.ai main leaderboard â overall ELO across all task categories.
    Source: https://arena.ai/leaderboard  Returns {model: elo_float}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Arena Overall (human preference)...")
        url = "https://arena.ai/leaderboard"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)
            try:
                view_all = page.locator("text=View all").first
                if view_all.count():
                    view_all.click()
                    page.wait_for_timeout(4000)
            except Exception:
                pass
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 10:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 2)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "elo" in h or "rating" in h), 3)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                raw_val = cells[score_col].get_text(strip=True).replace(',', '')
                m = re.match(r'^(\d{3,4}(?:\.\d+)?)', raw_val)
                if m:
                    try:
                        val = float(m.group(1))
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            if scores:
                break
        log.info(f"  â Arena Overall: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Arena Overall: {e}")
    return scores


def scrape_arena_text() -> dict[str, float]:
    """Arena text-specific leaderboard â ELO for text/chat tasks only.
    Source: https://arena.ai/leaderboard/text  (313 models, text-specific ELO)
    Distinct from the overall multi-category ELO. Returns {model: elo_float}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Arena Text (human preference)...")
        url = "https://arena.ai/leaderboard/text"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 2)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "elo" in h or "rating" in h), 3)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                raw_val = cells[score_col].get_text(strip=True).replace(',', '')
                m = re.match(r'^(\d{3,4}(?:\.\d+)?)', raw_val)
                if m:
                    try:
                        val = float(m.group(1))
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            if scores:
                break
        log.info(f"  â Arena Text: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ Arena Text not available: {e}")
    return scores


def scrape_alpacaeval() -> dict[str, float]:
    """AlpacaEval 2.0 â LC (length-controlled) win rate leaderboard.
    Source: https://tatsu-lab.github.io/alpaca_eval/
    68 models. LC win rate % vs GPT-4 baseline. Returns {model: pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping AlpacaEval (human preference)...")
        html = playwright_get("https://tatsu-lab.github.io/alpaca_eval/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "lc" in h or "win" in h or "rate" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*ð.*$', '', name).strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â AlpacaEval: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ AlpacaEval not available: {e}")
    return scores


# ââ SCRAPERS â KNOWLEDGE (8%) âââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 5: CODING (11%) âââââââââââââââââââââââââââââââââââââ
def scrape_swebench_verified() -> dict[str, float]:
    """swebench.com â verified split leaderboard. Returns {model: pct_resolved}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench Verified (coding)...")
        html = playwright_get("https://www.swebench.com/", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "instance" in h or "name" in h), 0)
            pct_col  = next((i for i, h in enumerate(headers)
                             if "resolve" in h or "%" in h or "score" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, pct_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                val  = cells[pct_col].get_text(strip=True).replace("%", "").strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        scores[name] = pct
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SWE-bench Verified: {len(scores)} models")
    except Exception as e:
        log.error(f"  â SWE-bench: {e}")
    return scores


def scrape_evalplus() -> dict[str, float]:
    """EvalPlus â HumanEval+ coding leaderboard.
    Source: https://evalplus.github.io/leaderboard.html
    250+ models. HumanEval+ pass@1 percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping EvalPlus (coding)...")
        html = playwright_get("https://evalplus.github.io/leaderboard.html", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            # Columns: rank | name | HumanEval+ | HumanEval++ | ...
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "humaneval" in h or "pass" in h or "score" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'[â¨ð¥ð¥ð¥ââ]', '', name).strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â EvalPlus: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ EvalPlus not available: {e}")
    return scores


def scrape_livecodebench() -> dict[str, float]:
    """LiveCodeBench â contamination-free coding leaderboard.
    Source: https://livecodebench.github.io/leaderboard.html
    28+ models. PASS@1 percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping LiveCodeBench (coding)...")
        html = playwright_get("https://livecodebench.github.io/leaderboard.html", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "pass" in h or "score" in h or "overall" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â LiveCodeBench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ LiveCodeBench not available: {e}")
    return scores


def scrape_swe_rebench() -> dict[str, float]:
    """SWE-rebench â continuously decontaminated SWE benchmark.
    Source: https://swe-rebench.com/leaderboard
    84 models. Resolved rate percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-rebench (coding)...")
        html = playwright_get("https://swe-rebench.com/leaderboard", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h or "system" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "resolve" in h or "%" in h or "score" in h or "pass" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SWE-rebench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ SWE-rebench not available: {e}")
    return scores


# ââ SCRAPERS â HUMAN PREFERENCE (18%) ââââââââââââââââââââââââââââ


def scrape_bigcodebench() -> dict[str, float]:
    """bigcode-bench.github.io â function calling + instruction following."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping BigCodeBench...")
        html = playwright_get(
            "https://bigcode-bench.github.io/", wait_ms=6000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            # Look for "Complete" or "Instruct" score â prefer Complete
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    pct = float(clean)
                    if 0 <= pct <= 100:
                        scores[name] = pct
                        break
                except ValueError:
                    pass
        log.info(f"  â BigCodeBench: {len(scores)} models")
    except Exception as e:
        log.error(f"  â BigCodeBench: {e}")
    return scores


def scrape_terminal_bench() -> dict[str, float]:
    """tbench.ai â Terminal-Bench Hard subset. Returns {model: accuracy_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Terminal-Bench Hard...")
        # FIX: correct URL â root page doesn't show table
        html = playwright_get("https://tbench.ai/leaderboard/terminal-bench/2.0", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")

        # Table columns: Rank, Agent, Model, Date, Agent Org, Model Org, Accuracy, CI
        # We want "Model" column for name and "Accuracy" column for score
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers) if h == "model"), None)
            acc_col   = next((i for i, h in enumerate(headers)
                              if "accuracy" in h or "score" in h), None)
            # Fallback column positions for typical terminal-bench layout
            if model_col is None:
                model_col = 2
            if acc_col is None:
                acc_col = 6
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, acc_col):
                    continue
                name = cells[model_col].get_text(strip=True)
                val  = cells[acc_col].get_text(strip=True)
                # FIX: strip "Â±" confidence intervals â "75.1% Â± 2.4" â "75.1"
                val = re.split(r'[Â±%]', val)[0].strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        # Keep best score if same model appears with multiple agents
                        if name not in scores or pct > scores[name]:
                            scores[name] = pct
                except ValueError:
                    pass
            if scores:
                break

        log.info(f"  â Terminal-Bench Hard: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Terminal-Bench: {e}")
    return scores


def scrape_swebench_pro() -> dict[str, float]:
    """scale.com/leaderboard/swe_bench_pro_public â harder SWE-bench variant."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench Pro (Scale AI)...")
        url = "https://scale.com/leaderboard/swe_bench_pro_public"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")

        # Scale AI renders as React button components â no tables, no __NEXT_DATA__.
        # Playwright renders JS; body text has lines like "claude-opus...\n45.89Â±3.60"
        # or score/Â± split across two separate lines: "45.89" then "Â±3.60"
        body_text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        score_re = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*[Â±]')
        for i, line in enumerate(lines):
            # Check this line, or this line + next line joined (handles split elements)
            peek = line
            if i + 1 < len(lines) and lines[i + 1].startswith('Â±'):
                peek = line + 'Â±'
            m = score_re.search(peek)
            if m:
                score_val = float(m.group(1))
                if 0 < score_val <= 100:
                    # Walk backward to find model name; skip bare numbers/symbols
                    for j in range(i - 1, max(-1, i - 6), -1):
                        candidate = lines[j].strip()
                        skip = re.match(r'^[\d\s\.Â±%+\-/]+$', candidate)
                        if candidate and not skip and len(candidate) > 4:
                            if candidate not in scores:
                                scores[candidate] = round(score_val, 2)
                            break

        log.info(f"  â SWE-bench Pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  â SWE-bench Pro: {e}")
    return scores


def scrape_scicode() -> dict[str, float]:
    """scicode-bench.github.io â scientific coding. Returns {model: main_resolve_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SciCode...")
        # FIX: correct URL â root page has no table; leaderboard is at /leaderboard/
        html = playwright_get("https://scicode-bench.github.io/leaderboard/", wait_ms=5000)
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h), 0)
            # FIX: prefer "main" problem resolve rate over subproblem
            main_col = next((i for i, h in enumerate(headers) if "main" in h), None)
            if main_col is None:
                main_col = 1  # fallback to first numeric column
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, main_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                val  = cells[main_col].get_text(strip=True).replace("%", "").strip()
                try:
                    pct = float(val)
                    # FIX: scores are already 0-100 (e.g. 10.8, 9.2) â do NOT multiply
                    if name and 0 <= pct <= 100:
                        scores[name] = round(pct, 2)
                except ValueError:
                    pass
            if scores:
                break

        log.info(f"  â SciCode: {len(scores)} models")
    except Exception as e:
        log.error(f"  â SciCode: {e}")
    return scores


def scrape_arena_code() -> dict[str, float]:
    """arena.ai/leaderboard/code â Code ELO. Returns {model: elo_score}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Chatbot Arena Code leaderboard...")
        url = "https://arena.ai/leaderboard/code"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")

        # arena.ai: server-side rendered HTML table (no __NEXT_DATA__)
        # Columns: Rank | Rank Spread | Model | Score | Votes
        # Model cell: "claude-opus-4-6\nAnthropic Â· Proprietary" â take first line
        # Score cell: "1561+14/-14" (no space before Â±) â extract leading integer
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 2)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "elo" in h or "rating" in h), 3)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                # First line of model cell only (skip "Provider Â· Type" suffix)
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                # Extract leading ELO integer â "1561+14/-14" or "1561 +14/-14"
                raw_val = cells[score_col].get_text(strip=True).replace(',', '')
                m = re.match(r'^(\d{3,4}(?:\.\d+)?)', raw_val)
                if m:
                    try:
                        val = float(m.group(1))
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            if scores:
                break

        log.info(f"  â Chatbot Arena Code: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Arena Code: {e}")
    return scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ



# âââ PILLAR 6: AGENT CAPABILITY (10%) âââââââââââââââââââââââââââ
def scrape_task_completion() -> dict[str, float]:
    """
    Task Completion pillar.
    Aggregates: SWE-bench Verified, GAIA, OSWorld, tau-bench
    Returns {model_name: pillar_score_0_to_100}
    """
    log.info("Scraping Task Completion pillar...")
    all_sources = []

    # ââ 1. SWE-bench Verified âââââââââââââââââââââââââââââââââââââ
    swe_scores: dict[str, float] = {}
    try:
        log.info("  - SWE-bench Verified...")
        html = playwright_get("https://www.swebench.com/", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "instance" in h or "name" in h), 0)
            pct_col  = next((i for i, h in enumerate(headers)
                             if "resolve" in h or "%" in h or "score" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, pct_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                val  = cells[pct_col].get_text(strip=True).replace("%", "").strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        swe_scores[name] = pct
                except ValueError:
                    pass
            if swe_scores:
                break
        log.info(f"    SWE-bench: {len(swe_scores)} models")
        if swe_scores:
            all_sources.append(swe_scores)
    except Exception as e:
        log.warning(f"    SWE-bench failed: {e}")

    # ââ 2. GAIA (HAL leaderboard) âââââââââââââââââââââââââââââââââ
    gaia_scores: dict[str, float] = {}
    try:
        log.info("  - GAIA...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
            page = ctx.new_page()
            try:
                page.goto("https://hal.cs.princeton.edu/gaia",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            page.wait_for_timeout(8000)
            rows = page.evaluate("""() => {
                const tables = document.querySelectorAll('table');
                if (!tables.length) return [];
                let best = tables[0];
                for (const t of tables) if (t.rows.length > best.rows.length) best = t;
                const allRows = Array.from(best.querySelectorAll('tr'));
                if (allRows.length < 2) return [];
                const headers = Array.from(allRows[0].querySelectorAll('th,td'))
                    .map(h => h.textContent.trim().toLowerCase());
                // GAIA uses 'primary model' (col 2) and 'accuracy' (col 4)
                const nameIdx = Math.max(0, headers.findIndex(
                    h => h.includes('primary') || h.includes('model') ||
                         h.includes('agent') || h.includes('system')));
                const scoreIdx = headers.findIndex(
                    h => h.includes('accuracy') || h.includes('avg') ||
                         h.includes('overall') || h.includes('total'));
                if (scoreIdx === -1) return [];
                return allRows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td,th'))
                        .map(td => td.textContent.trim());
                    return {model: cells[nameIdx] || '', score: cells[scoreIdx] || ''};
                }).filter(r => r.model && r.score);
            }""")
            browser.close()
        for row in rows:
            name = str(row.get('model', '')).strip()
            # Strip trailing date/version in parens: "Claude Sonnet 4.5 (September 2025)"
            name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
            score_raw = str(row.get('score', '')).strip()
            # Score may be "74.55% (-0.00/+0.00)" â extract first number only
            m = re.match(r'([\d.]+)', score_raw.replace('%', '').strip())
            if not name or not m:
                continue
            try:
                val = float(m.group(1))
                # Keep best score per model (multiple scaffold rows per model)
                if 0 < val <= 100:
                    if name not in gaia_scores or val > gaia_scores[name]:
                        gaia_scores[name] = val
            except ValueError:
                pass
        log.info(f"    GAIA: {len(gaia_scores)} models")
        if gaia_scores:
            all_sources.append(gaia_scores)
    except Exception as e:
        log.warning(f"    GAIA failed: {e}")

    # ââ 3. tau-bench âââââââââââââââââââââââââââââââââââââââââââââ
    tau_scores: dict[str, float] = {}
    try:
        log.info("  - tau-bench...")
        # Navigate to #leaderboard hash â the SPA only renders the table
        # after this hash is active. BeautifulSoup on the root URL misses it.
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
            page = ctx.new_page()
            try:
                page.goto("https://taubench.com/#leaderboard",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            page.wait_for_timeout(12000)
            rows = page.evaluate("""() => {
                const table = document.querySelector('table');
                if (!table) return [];
                const allRows = Array.from(table.querySelectorAll('tr'));
                if (allRows.length < 2) return [];
                // headers: Rank, Model, Submitting Org, User Sim, Pass^1, ...
                // col 1 = model name, col 4 = Pass^1 (primary score)
                return allRows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td,th'))
                        .map(td => td.textContent.replace(/[^\\w\\s.%\\-]/gu, '').trim());
                    return {model: cells[1] || '', score: cells[4] || ''};
                }).filter(r => r.model && r.score && r.score !== '' && r.score !== '-');
            }""")
            browser.close()
        for row in rows:
            name = str(row.get('model', '')).strip()
            # Strip warning emoji, "NEW" badge etc.
            name = re.sub(r'\s*(NEW|new)\s*$', '', name).strip()
            score_raw = str(row.get('score', '')).replace('%', '').strip()
            try:
                val = float(score_raw)
                if name and 0 < val <= 100:
                    tau_scores[name] = val
            except ValueError:
                pass
        log.info(f"    tau-bench: {len(tau_scores)} models")
        if tau_scores:
            all_sources.append(tau_scores)
    except Exception as e:
        log.warning(f"    tau-bench failed: {e}")

    # ââ 4. OSWorld âââââââââââââââââââââââââââââââââââââââââââââââ
    osworld_scores: dict[str, float] = {}
    try:
        log.info("  - OSWorld...")
        html = playwright_get("https://os-world.github.io/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h or "method" in h
                             or "agent" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "success" in h or "score" in h or "%" in h
                              or "result" in h or "overall" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, score_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                raw  = cells[score_col].get_text(strip=True).replace("%", "").strip()
                try:
                    val = float(raw)
                    if name and 0 <= val <= 100:
                        osworld_scores[name] = val
                except ValueError:
                    pass
            if osworld_scores:
                break
        log.info(f"    OSWorld: {len(osworld_scores)} models")
        if osworld_scores:
            all_sources.append(osworld_scores)
    except Exception as e:
        log.warning(f"    OSWorld failed: {e}")

    # ââ Aggregate: average of available sources per model âââââââââ
    scores: dict[str, float] = {}
    all_models: set[str] = set()
    for src in all_sources:
        all_models.update(src.keys())
    for model in all_models:
        vals = [src[model] for src in all_sources if model in src]
        if vals:
            scores[model] = round(sum(vals) / len(vals), 2)

    log.info(f"  â Task Completion: {len(scores)} models from {len(all_sources)} sources")
    return scores


def scrape_tool_reliability() -> dict[str, float]:
    """
    Tool Reliability pillar.
    Aggregates: SEAL Agentic Tool Use, Galileo agent leaderboard
    Returns {model_name: pillar_score_0_to_100}
    """
    log.info("Scraping Tool Reliability pillar...")
    all_sources = []

    # ââ 1. SEAL Agentic Tool Use (innerText) âââââââââââââââââââââ
    seal_scores: dict[str, float] = {}
    try:
        log.info("  - MCP Atlas (Scale AI / SEAL)...")
        # /agentic_tool_use is a 404 as of Feb 2026; replaced by /mcp_atlas
        text = playwright_get_innertext(
            "https://scale.com/leaderboard/mcp_atlas", wait_ms=12000)
        seal_scores = _parse_mcp_atlas_innertext(text)
        log.info(f"    MCP Atlas: {len(seal_scores)} models")
        if seal_scores:
            all_sources.append(seal_scores)
    except Exception as e:
        log.warning(f"    MCP Atlas failed: {e}")

    # ââ 2. Galileo agent leaderboard (HF Space) ââââââââââââââââââ
    galileo_scores: dict[str, float] = {}
    try:
        log.info("  - Galileo agent leaderboard...")
        html = playwright_get_hfspace(
            "https://huggingface.co/spaces/galileo-ai/agent-leaderboard",
            wait_ms=15000)
        rows = parse_first_table(html)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            trows = table.find_all("tr")
            if len(trows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in trows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h or "agent" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "%" in h or "pass" in h
                              or "success" in h or "overall" in h or "avg" in h), 1)
            for row in trows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, score_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                raw  = cells[score_col].get_text(strip=True).replace("%", "").strip()
                try:
                    val = float(raw)
                    if name and 0 <= val <= 100:
                        galileo_scores[name] = val
                except ValueError:
                    pass
            if galileo_scores:
                break
        # Galileo reports success rates as fractions (0.55) not percentages (55).
        # Detect this and scale up so scores are consistent 0â100.
        if galileo_scores and max(galileo_scores.values(), default=0) <= 1.0:
            galileo_scores = {k: round(v * 100, 2) for k, v in galileo_scores.items()}
            log.info("    Galileo: scaled fractional values Ã 100")
        log.info(f"    Galileo: {len(galileo_scores)} models")
        if galileo_scores:
            all_sources.append(galileo_scores)
    except Exception as e:
        log.warning(f"    Galileo failed: {e}")

    # ââ Aggregate âââââââââââââââââââââââââââââââââââââââââââââââââ
    scores: dict[str, float] = {}
    all_models: set[str] = set()
    for src in all_sources:
        all_models.update(src.keys())
    for model in all_models:
        vals = [src[model] for src in all_sources if model in src]
        if vals:
            scores[model] = round(sum(vals) / len(vals), 2)

    log.info(f"  â Tool Reliability: {len(scores)} models from {len(all_sources)} sources")
    return scores


def scrape_multi_model() -> dict[str, float]:
    """
    Multi-Model Support pillar.
    Source: OpenRouter rankings (most-used models by developers)
    Returns {model_name: pillar_score_0_to_100}
    """
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Multi-Model Support pillar (OpenRouter rankings)...")
        text = playwright_get_innertext("https://openrouter.ai/rankings", wait_ms=10000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        rank_num = 0
        for i, line in enumerate(lines):
            if re.match(r'^\d+\.$', line):
                rank_num = int(line[:-1])
                if i + 1 < len(lines):
                    name = lines[i + 1]
                    if name and len(name) > 2 and not name.lower().startswith("by "):
                        rank_score = max(0, 100 - ((rank_num - 1) * 2))
                        if rank_score > 0:
                            scores[name] = rank_score
        log.info(f"  â Multi-Model Support: {len(scores)} models from OpenRouter")
    except Exception as e:
        log.error(f"  â Multi-Model Support: {e}")
    return scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 7: KNOWLEDGE (8%) âââââââââââââââââââââââââââââââââââ
def scrape_mmlu_pro() -> dict[str, float]:
    """huggingface.co/spaces/TIGER-Lab/MMLU-Pro â knowledge leaderboard (via iframe)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping MMLU-Pro (knowledge)...")
        url = "https://huggingface.co/spaces/TIGER-Lab/MMLU-Pro"
        html = playwright_get_hfspace(url, wait_ms=15000)
        rows = parse_first_table(html)
        for row in rows:
            name = row.get("Models", "")
            if not name:
                vals = list(row.values())
                name = vals[0] if vals else ""
            if not name:
                continue
            overall_raw = row.get("Overall", "")
            if not overall_raw or overall_raw == "-":
                continue
            clean = overall_raw.replace("%", "").strip()
            try:
                val = float(clean)
                if 0 < val <= 1.0:
                    scores[name] = round(val * 100, 4)
                elif 1 < val <= 100:
                    scores[name] = val
            except ValueError:
                pass
        log.info(f"  â MMLU-Pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  â MMLU-Pro: {e}")
    return scores


def scrape_helm_mmlu() -> dict[str, float]:
    """HELM MMLU leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/mmlu/latest/#/leaderboard
    Accuracy on MMLU knowledge benchmark. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/mmlu/latest/#/leaderboard",
        "HELM MMLU",
        wait_ms=12000,
    )


def scrape_simpleqa_knowledge() -> dict[str, float]:
    """SimpleQA leaderboard via llm-stats.com.
    Source: https://llm-stats.com/benchmarks/simpleqa
    43 models. Factual accuracy 0-1 float. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SimpleQA (knowledge)...")
        html = playwright_get("https://llm-stats.com/benchmarks/simpleqa", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "accuracy" in h or "correct" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 1.0:
                        val = round(val * 100, 4)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SimpleQA: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ SimpleQA not available: {e}")
    return scores


# ââ SCRAPERS â EFFICIENCY (7%) ââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 8: FORECASTING & FINANCE (7%) âââââââââââââââââââââââ
def scrape_forecastbench() -> tuple[dict[str, float], dict[str, float]]:
    """
    ForecastBench baseline leaderboard (forecastbench.org/baseline/).
    Returns two dicts (both use the same Overall Brier score):
    - baseline Brier scores (0.0-1.0, lower is better)
    - tournament Brier scores (same source, reused for calibration)
    """
    baseline_scores = {}
    tournament_scores = {}
    try:
        log.info("Scraping ForecastBench...")
        # Table is JS-rendered -- use page.evaluate() to extract from live DOM
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://forecastbench.org/baseline/",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table", timeout=30_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const table = document.querySelector('table');
                if (!table) return [];
                const allRows = Array.from(table.querySelectorAll('tr'));
                const headers = Array.from(allRows[0].querySelectorAll('th,td'))
                    .map(el => el.textContent.trim());
                const modelIdx = headers.indexOf('Model');
                const overallIdx = headers.indexOf('Overall (N)');
                if (modelIdx === -1) return [];
                return allRows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {
                        model: cells[modelIdx] || '',
                        overall: overallIdx >= 0 ? cells[overallIdx] || '' : ''
                    };
                }).filter(r => r.model);
            }""")
            browser.close()

        SKIP = {"Superforecaster median forecast", "Public median forecast"}
        for row in rows:
            name = row.get("model", "")
            if not name or name in SKIP:
                continue
            overall_raw = row.get("overall", "")
            if not overall_raw:
                continue
            clean = overall_raw.split(" ")[0].replace(",", "").strip()
            try:
                val = float(clean)
                if 0 < val <= 1:
                    baseline_scores[name] = val
                    tournament_scores[name] = val  # reuse for calibration pillar
            except ValueError:
                pass

        log.info(f"  â ForecastBench: {len(baseline_scores)} baseline, {len(tournament_scores)} tournament")
    except Exception as e:
        log.error(f"  â ForecastBench: {e}")

    return baseline_scores, tournament_scores


def scrape_rallies() -> tuple[dict[str, float], dict[str, float]]:
    """
    Rallies.ai Arena leaderboard (rallies.ai/arena). Returns two dicts:
    - return_pct: portfolio Return % (column "Return %")
    - win_rate_pct: Win Rate % (column "Win Rate")
    """
    return_scores = {}
    winrate_scores = {}
    try:
        log.info("Scraping Rallies.ai...")
        # NOTE: old URL rallies.ai/ has no table -- leaderboard is at rallies.ai/arena
        html = playwright_get("https://rallies.ai/arena", wait_ms=10000)
        rows = parse_first_table(html)

        for row in rows:
            name = row.get("Model", "")
            if not name:
                vals = list(row.values())
                name = vals[1] if len(vals) > 1 else ""  # col 0 is rank emoji
            if not name:
                continue
            # Return % -- may start with "up" or "down" or be plain number
            ret_raw = row.get("Return %", "")
            try:
                val = float(ret_raw.replace("%", "").replace("+", "").strip())
                if -1000 <= val <= 10000:
                    return_scores[name] = val
            except ValueError:
                pass
            # Win Rate
            wr_raw = row.get("Win Rate", "")
            try:
                val = float(wr_raw.replace("%", "").strip())
                if 0 <= val <= 100:
                    winrate_scores[name] = val
            except ValueError:
                pass

        log.info(f"  Rallies.ai: {len(return_scores)} returns, {len(winrate_scores)} win rates")
    except Exception as e:
        log.error(f"  Rallies.ai: {e}")

    return return_scores, winrate_scores
def scrape_alpha_arena() -> tuple[dict[str, float], dict[str, float]]:
    """
    Alpha Arena (nof1.ai/leaderboard) leaderboard. Returns two dicts:
    - return_pct: portfolio Return % (best per base model)
    - sharpe_ratio: Sharpe ratio (best per base model)
    Model names have strategy suffixes stripped: "GROK-4.20 - 3: SITUATIONAL AWARENESS" -> "GROK-4.20"
    """
    return_scores = {}
    sharpe_scores = {}
    try:
        log.info("Scraping Alpha Arena...")
        # NOTE: old URL nof1.ai/ has no table -- leaderboard is at nof1.ai/leaderboard
        html = playwright_get("https://nof1.ai/leaderboard", wait_ms=10000)
        rows = parse_first_table(html)

        for row in rows:
            raw_name = row.get("MODEL", "")
            if not raw_name:
                vals = list(row.values())
                raw_name = vals[1] if len(vals) > 1 else ""  # col 0 is rank
            if not raw_name:
                continue
            # Strip strategy suffix: "GROK-4.20 - 3: SITUATIONAL AWARENESS" -> "GROK-4.20"
            name = re.sub(r'\s*-\s*\d+:\s*.+$', '', raw_name).strip()
            if not name:
                continue
            # Return %: "+34.59%" or "-10.45%"
            ret_raw = row.get("RETURN %", "")
            try:
                val = float(ret_raw.replace("%", "").replace("+", "").strip())
                if name not in return_scores or val > return_scores[name]:
                    return_scores[name] = val
            except ValueError:
                pass
            # Sharpe ratio (can be negative)
            sharpe_raw = row.get("SHARPE", "")
            try:
                val = float(sharpe_raw.strip())
                if name not in sharpe_scores or val > sharpe_scores[name]:
                    sharpe_scores[name] = val
            except ValueError:
                pass

        log.info(f"  Alpha Arena: {len(return_scores)} returns, {len(sharpe_scores)} Sharpe")
    except Exception as e:
        log.error(f"  Alpha Arena: {e}")

    return return_scores, sharpe_scores
def scrape_financearena() -> tuple[dict[str, float], dict[str, float]]:
    """
    FinanceArena leaderboard. Returns two dicts:
    - qa_pct: QA accuracy (%)
    - elo_score: ELO rating
    """
    qa_scores = {}
    elo_scores = {}
    try:
        log.info("Scraping FinanceArena...")
        html = playwright_get("https://financearena.ai/", wait_ms=8000)
        rows = parse_first_table(html)
        
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            
            # Try to extract QA accuracy and ELO
            if len(vals) > 1:
                try:
                    val = float(vals[1].replace("%", "").strip())
                    if 0 <= val <= 100:
                        qa_scores[name] = val
                except (ValueError, IndexError):
                    pass
            if len(vals) > 2:
                try:
                    val = float(vals[2].replace("%", "").strip())
                    if 0 <= val <= 3000:  # Typical ELO range
                        elo_scores[name] = val
                except (ValueError, IndexError):
                    pass
        
        log.info(f"  â FinanceArena: {len(qa_scores)} QA, {len(elo_scores)} ELO")
    except Exception as e:
        log.error(f"  â FinanceArena: {e}")
    
    return qa_scores, elo_scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ


# âââ PILLAR 9: EFFICIENCY (5%) ââââââââââââââââââââââââââââââââââ
def scrape_artificial_analysis() -> dict[str, float]:
    """artificialanalysis.ai/leaderboards/models -- efficiency (Median Tokens/s)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Artificial Analysis (efficiency)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://artificialanalysis.ai/leaderboards/models",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr:nth-child(3)", timeout=30_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const table = document.querySelector('table');
                if (!table) return [];
                const allRows = Array.from(table.querySelectorAll('tr'));
                return allRows.slice(2).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {model: cells[0] || '', speed: cells[5] || ''};
                }).filter(r => r.model && r.speed);
            }""")
            browser.close()

        for row in rows:
            name = row.get("model", "")
            name = re.sub(r'\s*\([^)]+\)\s*$', '', name).strip()
            if not name:
                continue
            speed_raw = row.get("speed", "")
            try:
                val = float(speed_raw.replace(",", "").strip())
                if val > 0:
                    scores[name] = val
            except ValueError:
                pass
        log.info(f"  â Artificial Analysis: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Artificial Analysis: {e}")
    return scores


def scrape_pricepertoken() -> dict[str, float]:
    """PricePerToken â $/M input tokens leaderboard.
    Source: https://pricepertoken.com
    298 models. Lower price = better efficiency. Score inverted: cheapest = 100.
    Returns {model: inverted_score_0_to_100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping PricePerToken (efficiency)...")
        html = playwright_get("https://pricepertoken.com", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            # Prefer "input" pricing column ($/M tokens input)
            price_col = next((i for i, h in enumerate(headers)
                              if "input" in h), None)
            if price_col is None:
                price_col = next((i for i, h in enumerate(headers)
                                  if "price" in h or "$" in h or "cost" in h), 2)
            raw_prices: dict[str, float] = {}
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, price_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                price_raw = cells[price_col].get_text(strip=True).replace('$', '').replace(',', '').strip()
                try:
                    price = float(price_raw)
                    if price >= 0:
                        raw_prices[name] = price
                except ValueError:
                    pass
            if raw_prices:
                # Invert: cheapest model gets highest score
                # Use log scale to handle wide price ranges (free to $$$)
                import math
                min_price = min(v for v in raw_prices.values() if v > 0) if any(v > 0 for v in raw_prices.values()) else 0.001
                for name, price in raw_prices.items():
                    effective = max(price, min_price * 0.1)
                    # Higher score = cheaper. Score = 100 * (min_price / price)
                    inv_score = round(100.0 * min_price / effective, 4)
                    scores[name] = min(inv_score, 100.0)
                break
        log.info(f"  â PricePerToken: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ PricePerToken not available: {e}")
    return scores


# ââ SCRAPERS â USAGE ADOPTION (6%) ââââââââââââââââââââââââââââââââ


# âââ PILLAR 10: USAGE / ADOPTION (5%) âââââââââââââââââââââââââââ
def scrape_openrouter_usage() -> dict[str, float]:
    """openrouter.ai/rankings â usage adoption scores (innerText parse, no <table>)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping OpenRouter Rankings (usage adoption)...")
        url = "https://openrouter.ai/rankings"
        text = playwright_get_innertext(url, wait_ms=10000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        rank_num = 0
        for i, line in enumerate(lines):
            if re.match(r'^\d+\.$', line):
                rank_num = int(line[:-1])
                if i + 1 < len(lines):
                    name = lines[i + 1]
                    if name and len(name) > 2 and not name.lower().startswith("by "):
                        rank_score = max(0, 100 - ((rank_num - 1) * 2))
                        if rank_score > 0:
                            scores[name] = rank_score
        log.info(f"  â OpenRouter Rankings: {len(scores)} models")
    except Exception as e:
        log.error(f"  â OpenRouter Rankings: {e}")
    return scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ



# âââ PILLAR â SCRAPER MAPPING âââââââââââââââââââââââââââââââââââ
PILLAR_SCRAPERS = {
    "safety": [
        scrape_helm_safety,
        scrape_airbench,
    ],
    "truth_confabulation": [
        scrape_simpleqa,
        scrape_facts,
        scrape_truthfulqa,
        scrape_halluhard,
        scrape_vectara_hallucination,
    ],
    "reasoning": [
        scrape_arc_agi2,
        scrape_livebench_reasoning,
        scrape_helm_capabilities,
        scrape_hle,
    ],
    "human_preference": [
        scrape_arena_overall,
        scrape_arena_text,
        scrape_alpacaeval,
    ],
    "coding": [
        scrape_swebench_verified,
        scrape_evalplus,
        scrape_livecodebench,
        scrape_swe_rebench,
        scrape_bigcodebench,
        scrape_terminal_bench,
        scrape_swebench_pro,
        scrape_scicode,
        scrape_arena_code,
    ],
    "agent_capability": [
        scrape_task_completion,
        scrape_tool_reliability,
        scrape_multi_model,
    ],
    "knowledge": [
        scrape_mmlu_pro,
        scrape_helm_mmlu,
        scrape_simpleqa_knowledge,
    ],
    "forecasting_finance": [
        scrape_forecastbench,
        scrape_rallies,
        scrape_alpha_arena,
        scrape_financearena,
    ],
    "efficiency": [
        scrape_artificial_analysis,
        scrape_pricepertoken,
    ],
    "usage_adoption": [
        scrape_openrouter_usage,
    ],
}


# âââ SCORING ENGINE âââââââââââââââââââââââââââââââââââââââââââââ

def normalize_sources_and_merge(scraper_list: list) -> tuple[dict[str, float], int]:
    """
    Run all scrapers for a pillar. For each source:
      1. Normalize to 0-100 (top model in that source = 100)
      2. Merge by averaging normalized scores across sources
    Returns merged {model: avg_normalized_score}.
    Models appearing in more sources get their scores averaged.
    """
    merged: dict[str, float] = {}
    counts: dict[str, int] = {}
    sources_hit = 0
    for scraper_fn in scraper_list:
        raw = scraper_fn()
        if not raw:
            continue
        # Handle scrapers returning multiple dicts (e.g. forecast sub-metrics)
        dicts_to_process = list(raw) if isinstance(raw, (tuple, list)) else [raw]
        for d in dicts_to_process:
            if not isinstance(d, dict) or not d:
                continue
            top = max(d.values())
            if top <= 0:
                continue
            sources_hit += 1
            for model, val in d.items():
                norm = (val / top) * 100.0
                merged[model] = merged.get(model, 0.0) + norm
                counts[model] = counts.get(model, 0) + 1
    if not merged:
        return {}, 0
    return {m: round(merged[m] / counts[m], 4) for m in merged}, sources_hit



def calculate_composite(model_name: str, normalized: dict) -> tuple:
    """
    TR2-unified-v1.3 composite score with coverage bonus.
    Weighted average across available pillars (weights renormalized).
    Coverage bonus: 3% per pillar above 5 pillars covered.
    """
    total_pillars = len(WEIGHTS)
    available_weights = {k: WEIGHTS[k] for k in WEIGHTS
                         if normalized.get(k, {}).get(model_name, None) is not None
                         and normalized[k].get(model_name, 0.0) > 0}
    if not available_weights:
        return 0.0, 0
    weight_sum = sum(available_weights.values())
    raw_score = sum(
        normalized[k][model_name] * (WEIGHTS[k] / weight_sum)
        for k in available_weights
    )
    covered = len(available_weights)
    bonus_pillars = max(0, covered - 5)
    bonus = 1.0 + (0.03 * bonus_pillars)
    final = round(raw_score * bonus, 2)
    return min(final, 100.0), covered


def _infer_company(name: str) -> str:
    """Best-effort company inference from model name keywords."""
    n = name.lower()
    if any(x in n for x in ["gpt", "o1-", "o3-", "o4-", "chatgpt", "davinci"]):
        return "OpenAI"
    if any(x in n for x in ["claude", "opus", "sonnet", "haiku"]):
        return "Anthropic"
    if any(x in n for x in ["gemini", "gemma", "bard"]):
        return "Google"
    if any(x in n for x in ["grok"]):
        return "xAI"
    if any(x in n for x in ["llama", "meta-", "turbo"]):
        return "Meta"
    if any(x in n for x in ["mistral", "mixtral", "pixtral", "codestral", "voxtral", "devstral"]):
        return "Mistral"
    if any(x in n for x in ["deepseek"]):
        return "DeepSeek"
    if any(x in n for x in ["qwen", "qwq"]):
        return "Alibaba"
    if any(x in n for x in ["glm", "chatglm", "zhipu"]):
        return "Zhipu AI"
    if any(x in n for x in ["minimax"]):
        return "MiniMax"
    if any(x in n for x in ["command", "cohere", "aya"]):
        return "Cohere"
    if any(x in n for x in ["moonshot", "kimi"]):
        return "Moonshot AI"
    if any(x in n for x in ["nova", "titan", "amazon"]):
        return "Amazon"
    if any(x in n for x in ["phi-", "copilot", "wizardlm"]):
        return "Microsoft"
    if any(x in n for x in ["nemotron", "nvidia"]):
        return "NVIDIA"
    if any(x in n for x in ["falcon"]):
        return "TII"
    if any(x in n for x in ["yi-", "01.ai"]):
        return "01.AI"
    if any(x in n for x in ["granite", "ibm"]):
        return "IBM"
    if any(x in n for x in ["olmo", "olmoe", "molmo", "tulu"]):
        return "AI2"
    if any(x in n for x in ["palmyra", "palm", "writer"]):
        return "Writer"
    if any(x in n for x in ["dbrx", "databricks"]):
        return "Databricks"
    if any(x in n for x in ["mercury", "inception"]):
        return "Inception"
    if any(x in n for x in ["intellect"]):
        return "PrimeIntellect"
    return "Unknown"


AUTO_DISCOVER_MIN_SOURCES = 2  # model must appear in 2+ pillars to join roster



# âââ MODEL NAME REGISTRY ââââââââââââââââââââââââââââââââââââââââ
CANONICAL_ROSTER = [
    # Anthropic
    "Claude Opus 4.6",
    "Claude Opus 4.5",
    "Claude Opus 4.1",
    "Claude Sonnet 4.6",
    "Claude Sonnet 4.5",
    "Claude Code",
    "Claude 3 Haiku",
    "Claude 2.1",
    # OpenAI
    "GPT-5.2",
    "GPT-5.1",
    "GPT-5",
    "GPT-5 mini",
    "GPT-4",
    "GPT-4o",
    "GPT-4.5",
    "GPT-3.5 Turbo",
    "O3",
    "o3-mini",
    "o4-mini",
    "o1-preview",
    "o1-mini",
    "gpt-oss-120b",
    # Google / DeepMind
    "Gemini 3 Pro",
    "Gemini 3 Flash",
    "Gemini 2.5 Pro",
    "Gemini Flash 3",
    "Gemma 3 12B",
    "Palmyra X5",
    "Palmyra-X-004",
    "Palmyra Fin",
    "Palmyra Med",
    # xAI
    "Grok 4.20",
    "Grok 4.1",
    "Grok 3 Beta",
    # DeepSeek
    "DeepSeek V3.2",
    "DeepSeek V3.1",
    "DeepSeek-V3",
    "DeepSeek R1",
    "DeepSeek LLM Chat",
    # Zhipu AI
    "GLM-5",
    "GLM-4",
    # Meta
    "Llama 4.08B",
    "Llama 4.05B",
    "Llama 4.0",
    "Llama 4 Maverick",
    "Llama 3.1 Instruct Turbo",
    # Mistral AI
    "Mistral Large 3",
    "Mistral Large",
    "Mistral Voxtral",
    "Devstral 2",
    "Mixtral Instruct",
    "Mistral Instruct v0.3",
    # Alibaba
    "Qwen3-Coder",
    "Qwen3",
    "Qwen2.5",
    "Qwen2 Instruct",
    "Qwen1.5 Chat",
    "qwq-32b",
    # MiniMax
    "MiniMax M2.5",
    "MiniMax M2",
    "MiniMax M1",
    # Moonshot AI
    "Kimi K2.5",
    "Kimi K2 Instruct",
    # Cohere
    "Cohere Command R+",
    "Command R Plus",
    "Cohere Aya",
    # PrimeIntellect / AI2 / others
    "intellect-3",
    "BLACKBOXAI",
    "INTELLECT-3",
    "K-EXAONE",
    "NVARC",
    "IBM Granite 3.3 8B Instruct",
    "Amazon Nova Lite",
    "Gemma 3 12B",
]

# ââ Explicit alias map âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# Keys are lowercase. Values are canonical names.
# Covers: emoji prefixes, short Claude names, casing variants, raw API names,
# version-number formats, and source-specific quirks.
ALIASES: dict[str, str] = {
    # ââ Claude: missing "Claude " prefix (Rallies, ForecastBench) ââ
    "opus 4.6":                               "Claude Opus 4.6",
    "opus 4.5":                               "Claude Opus 4.5",
    "opus 4.1":                               "Claude Opus 4.1",
    "sonnet 4.6":                             "Claude Sonnet 4.6",
    "sonnet 4.5":                             "Claude Sonnet 4.5",
    "haiku 4.5":                              "Claude 3 Haiku",
    # ââ Claude: raw API model IDs ââ
    "claude-opus-4-6":                        "Claude Opus 4.6",
    "claude-opus-4-5":                        "Claude Opus 4.5",
    "claude-sonnet-4-6":                      "Claude Sonnet 4.6",
    "claude-sonnet-4-5":                      "Claude Sonnet 4.5",
    "claude-haiku-4-5-20251001 (zero shot)":  "Claude 3 Haiku",
    "claude-haiku-4-5-20251001":              "Claude 3 Haiku",
    "claude-haiku-4.5-20251001":              "Claude 3 Haiku",
    # ââ OpenAI: spacing / dash variants ââ
    "gpt 5.2":                                "GPT-5.2",
    "gpt5.2":                                 "GPT-5.2",
    "gpt 5.1":                                "GPT-5.1",
    "gpt5.1":                                 "GPT-5.1",
    "gpt 5 mini":                             "GPT-5 mini",
    "gpt-5 mini":                             "GPT-5 mini",
    "gpt5 mini":                              "GPT-5 mini",
    "gpt 5.2 codex":                          "GPT-5.2",
    "gpt-5.2 codex":                          "GPT-5.2",
    "gpt-5-codex":                            "GPT-5.2",
    "chatgpt-4o-latest":                      "GPT-4o",
    "gpt-4o-2024-11-20":                      "GPT-4o",
    "gpt-4.5-preview-2025-02-27 (scratchpad)":"GPT-4.5",
    "gpt-4.5-preview":                        "GPT-4.5",
    "gpt-4.1 (2025-04-14)":                   "GPT-4",
    "gpt-4 turbo":                            "GPT-4",
    "gpt-4-turbo":                            "GPT-4",
    "gpt 4.1 mini":                           "GPT-4",
    "gpt-4.1 mini":                           "GPT-4",
    "gpt-oss-120b":                           "gpt-oss-120b",
    "gpt oss 120b":                           "gpt-oss-120b",
    "gpt-oss-120b (2506)":                    "gpt-oss-120b",
    "gpt oss 120b (2506)":                    "gpt-oss-120b",
    # ââ OpenAI: o-series ââ
    "o3":                                     "O3",
    "openai o3":                              "O3",
    "openai-o3":                              "O3",
    "o3 mini":                                "o3-mini",
    "openai o3-mini":                         "o3-mini",
    "o4 mini":                                "o4-mini",
    "openai o4-mini":                         "o4-mini",
    "openai o1 mini":                         "o1-mini",
    "openai o1-mini":                         "o1-mini",
    "openai o1 preview":                      "o1-preview",
    "openai o1-preview":                      "o1-preview",
    # ââ Google Gemini ââ
    "gemini-3-pro":                           "Gemini 3 Pro",
    "gemini-3-flash":                         "Gemini 3 Flash",
    "gemini-2.5-pro":                         "Gemini 2.5 Pro",
    "gemini-flash-3":                         "Gemini Flash 3",
    "gemini flash 3.0":                       "Gemini Flash 3",
    "gemini-3.0-flash":                       "Gemini Flash 3",
    # ââ xAI Grok ââ
    "grok-4":                                 "Grok 4.20",
    "grok 4":                                 "Grok 4.20",
    "grok4":                                  "Grok 4.20",
    "grok-4.20":                              "Grok 4.20",
    "grok 4.1":                               "Grok 4.1",
    "grok 3":                                 "Grok 3 Beta",
    "grok-3":                                 "Grok 3 Beta",
    "grok3":                                  "Grok 3 Beta",
    "grok-3-beta":                            "Grok 3 Beta",
    # ââ DeepSeek ââ
    "deepseek-v3":                            "DeepSeek-V3",
    "deepseek v3":                            "DeepSeek-V3",
    "deepseekv3":                             "DeepSeek-V3",
    "deepseek-r1 (scratchpad)":               "DeepSeek R1",
    "deepseek-r1":                            "DeepSeek R1",
    "deepseek r1":                            "DeepSeek R1",
    "deepseek-r1-zero":                       "DeepSeek R1",
    # ââ Qwen / Alibaba ââ
    "qwen3-max":                              "Qwen3",
    "qwen 3":                                 "Qwen3",
    "qwen3 30b a3b":                          "Qwen3",
    "qwen3-coder 480b/a35b instruct":         "Qwen3-Coder",
    "qwq-32b":                                "qwq-32b",
    "qwq 32b":                                "qwq-32b",
    # ââ MiniMax ââ
    "minimax m1 40k":                         "MiniMax M1",
    "minimax-m1-40k":                         "MiniMax M1",
    # ââ Kimi ââ
    "kimi-k2-thinking":                       "Kimi K2.5",
    "kimi k2 thinking":                       "Kimi K2.5",
    "kimi k2.5":                              "Kimi K2.5",
    "kimi-k2.5":                              "Kimi K2.5",
    # ââ Mistral ââ
    "devstral (2512)":                        "Devstral 2",
    "devstral":                               "Devstral 2",
    "mistral-large":                          "Mistral Large",
    # ââ Cohere ââ
    "command r+":                             "Cohere Command R+",
    "command-r+":                             "Cohere Command R+",
    "command a":                              "Command R Plus",
    # ââ Llama ââ
    "llama 4 maverick instruct":              "Llama 4 Maverick",
    "llama-4-maverick":                       "Llama 4 Maverick",
    "meta-llama/llama-4-maverick":            "Llama 4 Maverick",
    # ââ Misc scraped format quirks ââ
    "magistral medium":                       "Mistral Large",   # Magistral is Mistral
    "intellect 3":                            "intellect-3",
    "intellect-3":                            "intellect-3",
    # ââ GPT-4.5 long raw API names ââ
    "gpt-4.5-preview-2025-02-27":             "GPT-4.5",
    "gpt-4.5-preview":                        "GPT-4.5",
    # ââ Qwen large instruct variants â base name ââ
    "qwen3-coder 480b/a35b instruct":         "Qwen3-Coder",
    "qwen3 coder 480b/a35b instruct":         "Qwen3-Coder",
    # ââ Claude Haiku variants ââ
    "claude 4.5 haiku":                       "Claude 3 Haiku",
    "claude haiku 4.5":                       "Claude 3 Haiku",
    "claude 4.5 haiku (high reasoning)":      "Claude 3 Haiku",
    # ââ Amazon ââ
    "nova-pro-v1:0":                          "Amazon Nova Lite",
    "amazon/nova-pro-v1:0":                   "Amazon Nova Lite",
}


def _strip_noise(name: str) -> str:
    """Remove emoji prefixes, org-path prefixes (org/model), and common
    raw-API suffixes like '(zero shot)', '(scratchpad)', '(thinking)'."""
    # Strip leading emoji / non-ASCII decoration (e.g. ð, â)
    s = re.sub(r'^[\U00010000-\U0010ffff\U00002600-\U000027BF\U0001F300-\U0001FAFF]+\s*', '', name)
    # Strip org prefix ONLY when it looks like a pure lowercase slug
    # e.g. "anthropic/claude-opus-4-6" â "claude-opus-4-6"
    # but NOT "Qwen3-Coder 480B/A35B Instruct" (has uppercase / spaces before /)
    if '/' in s:
        before, after = s.split('/', 1)
        if re.match(r'^[a-z0-9\-_]+$', before):   # org-slug pattern only
            s = after
    # Strip trailing raw-API suffixes
    s = re.sub(r'\s*\((zero shot|scratchpad|thinking|high reasoning)\)\s*$', '', s, flags=re.IGNORECASE)
    return s.strip()


def _normalize(name: str) -> str:
    """Lowercase, collapse whitespace, normalize dashes/underscores for fuzzy
    token-overlap matching. Does NOT alter the displayed name."""
    s = _strip_noise(name).lower()
    s = s.replace('_', ' ').replace('-', ' ')
    # Normalize version separators: "4-5" â "4.5", "v3" â "3"
    s = re.sub(r'(\d)\s*-\s*(\d)', r'\1.\2', s)
    s = re.sub(r'\bv(\d)', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def canonicalize(name: str) -> str:
    """
    Normalize a scraped model name to its canonical display form.

    Steps:
      1. Strip emoji / org prefixes / raw-API suffixes.
      2. Expand known short Claude names: "Opus 4.6" â "Claude Opus 4.6".
      3. Look up in ALIASES (case-insensitive).
      4. Check CANONICAL_ROSTER for exact match.
      5. Return the cleaned name if no canonical match found.
    """
    if not name or not name.strip():
        return name

    cleaned = _strip_noise(name)
    cl = cleaned.lower()

    # Step 2: Expand short Claude model names missing the "Claude " prefix
    _CLAUDE_SHORT = [
        ("opus ",    "Claude Opus "),
        ("sonnet ",  "Claude Sonnet "),
        ("haiku ",   "Claude Haiku "),
    ]
    for short_prefix, full_prefix in _CLAUDE_SHORT:
        if cl.startswith(short_prefix) and not cl.startswith("claude"):
            expanded = full_prefix + cleaned[len(short_prefix):]
            cl_exp = expanded.lower()
            if cl_exp in ALIASES:
                return ALIASES[cl_exp]
            for c in CANONICAL_ROSTER:
                if c.lower() == cl_exp:
                    return c
            return expanded  # best-effort

    # Step 3: ALIASES lookup
    if cl in ALIASES:
        return ALIASES[cl]

    # Step 4: CANONICAL_ROSTER exact match
    for c in CANONICAL_ROSTER:
        if c.lower() == cl:
            return c

    # Step 5: Return cleaned name (emoji / suffix stripped)
    return cleaned


def match_name(scraped: str, existing: list[str]) -> str | None:
    """
    Find the best match for `scraped` within the `existing` name list.

    Matching tiers (first hit wins):
      1. Canonicalize both sides â exact match
      2. Substring containment (normalized)
      3. â¥2 token overlap (normalized)

    Returns the matched name from `existing`, or None if no match.
    """
    if not scraped:
        return None

    canon = canonicalize(scraped)
    canon_norm = _normalize(canon)

    # Tier 1: exact canonical match
    for name in existing:
        if canonicalize(name).lower() == canon.lower():
            return name
        if name.lower() == canon.lower():
            return name

    # Tier 2: substring containment (normalized)
    for name in existing:
        n = _normalize(name)
        if canon_norm in n or n in canon_norm:
            return name

    # Tier 3: â¥2 token overlap (normalized)
    c_tok = set(canon_norm.split())
    for name in existing:
        n_tok = set(_normalize(name).split())
        if len(c_tok & n_tok) >= 2:
            return name

    return None



# âââ GIT HELPERS ââââââââââââââââââââââââââââââââââââââââââââââââ

def git_push(commit_msg: str) -> bool:
    if DRY_RUN:
        log.info(f"[DRY RUN] Would commit: {commit_msg}")
        return True
    try:
        subprocess.run(["git", "-C", str(REPO_PATH), "add",
                        "trs-data-unified.json", "status.json"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(REPO_PATH), "commit", "-m", commit_msg],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(REPO_PATH), "pull", "--rebase"],
                       check=True, capture_output=True, timeout=60)
        result = subprocess.run(["git", "-C", str(REPO_PATH), "push"],
                                check=True, capture_output=True, timeout=60)
        log.info("Git push OK")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git failed: {e.stderr.decode() if e.stderr else e}")
        return False
    except subprocess.TimeoutExpired:
        log.error("Git push timed out")
        return False


def write_status(status: str, ranked: list, source_summary: list,
                 duration: float, sources_hit: int) -> None:
    sdata = {}
    if STATUS_FILE.exists():
        try:
            sdata = json.loads(STATUS_FILE.read_text())
        except Exception:
            pass

    now_iso = datetime.now().isoformat()
    top5 = []
    for m in ranked[:5]:
        sc = m["scores"][-1] if m["scores"] else None
        if sc is not None:
            top5.append({"rank": m.get("display_rank", 0), "name": m["name"], "score": sc})

    sdata["last_updated"] = now_iso
    sdata["tr2_unified"] = {
        "name":             "Gimli â TR2 Unified DDP",
        "enabled":          True,
        "last_run":         now_iso,
        "last_run_date":    TODAY,
        "status":           status,
        "duration_seconds": round(duration, 1),
        "sources_total":    TOTAL_SOURCES,
        "sources_hit":      sources_hit,
        "models_qualified": len(ranked),
        "top_model":        ranked[0]["name"] if ranked else None,
        "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
        "top5":             top5,
    }
    STATUS_FILE.write_text(json.dumps(sdata, indent=2))
    log.info(f"Wrote {STATUS_FILE.name}")


def auto_discover_models(data: dict, all_results: dict) -> list:
    known = {m["name"].lower() for m in data["models"]}
    discovered = set()
    for category, scores in all_results.items():
        for raw_name in scores:
            canon = canonicalize(raw_name)
            if canon.lower() not in known and len(canon) > 2:
                discovered.add(canon)
    discovered = {n for n in discovered if not n.startswith("(") and len(n) < 60}
    return sorted(discovered)



# âââ MAIN âââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def main():
    import time as _time
    start_time = _time.time()

    if TEST_TELEGRAM:
        notify("âï¸ <b>Gimli online</b>\nTelegram works!")
        print("Telegram test sent.")
        return

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(f"âï¸ Gimli | {TODAY} | {mode}")
    notify(f"âï¸ <b>Gimli | TR2 DDP starting</b>\n{TODAY}\n{mode}\n{TOTAL_SOURCES} sources")

    # Load data
    if not DATA_FILE.exists():
        msg = f"trs-data-unified.json not found at {DATA_FILE}"
        log.error(msg); notify(f"âï¸ <b>Gimli | ERROR</b>\n{msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"âï¸ Loaded. Models: {len(models)} | Dates: {dates[0]} to {dates[-1]}")

    # Date slot
    if TODAY in dates:
        date_is_new = False
        today_idx   = dates.index(TODAY)
        log.info(f"Overwriting existing date slot: {TODAY}")
    else:
        date_is_new = True
        dates.append(TODAY)
        today_idx = len(dates) - 1
        log.info(f"New date slot: {TODAY} (idx {today_idx})")

    # Scrape all pillars
    all_results = {}
    normalized  = {}
    total_sources_hit = 0
    source_summary = []

    for category, scraper_list in PILLAR_SCRAPERS.items():
        log.info(f"--- {PILLAR_NAMES.get(category, category)} ({len(scraper_list)} sources) ---")
        result, sources_hit = normalize_sources_and_merge(scraper_list)
        all_results[category] = result
        normalized[category]  = result
        total_sources_hit += sources_hit

        matched = sum(1 for name in result if match_name(name, names))
        source_summary.append(
            f"{PILLAR_NAMES.get(category, category)}: {sources_hit}/{len(scraper_list)} live, "
            f"{len(result)} scraped, {matched} matched"
        )
        log.info(f"  {sources_hit}/{len(scraper_list)} sources | "
                 f"{len(result)} models | {matched} matched")

    notify("âï¸ <b>Gimli | Scraping complete</b>\n" + "\n".join(source_summary))

    # Auto-discover new models
    new_models = auto_discover_models(data, all_results)
    if new_models:
        log.info(f"Auto-discovered {len(new_models)} new models")
        for nm in new_models:
            company = _infer_company(nm)
            models.append({
                "name": nm, "company": company,
                "scores": [None] * today_idx,
                "pillar_scores": {p: None for p in PILLAR_ORDER},
                "category_count": 0, "source_count": 0,
                "tier": "minimal", "benchmarks": {}, "display_rank": 0,
            })
            names.append(nm)

    # Calculate composite scores
    for model in models:
        n = model["name"]
        for cat, cat_scores in normalized.items():
            for scraped_name in cat_scores:
                if match_name(scraped_name, [n]):
                    normalized[cat][n] = cat_scores[scraped_name]
                    break

        sc, covered = calculate_composite(n, normalized)
        model["category_count"] = covered

        src_count = 0
        for cat, cat_scores in all_results.items():
            for scraped_name in cat_scores:
                if match_name(scraped_name, [n]):
                    src_count += 1
                    break
        model["source_count"] = src_count

        if date_is_new:
            model["scores"].append(sc if sc > 0 else None)
        else:
            while len(model["scores"]) <= today_idx:
                model["scores"].append(None)
            if sc > 0:
                model["scores"][today_idx] = sc

        pillar_scores = {}
        for cat in PILLAR_ORDER:
            val = normalized.get(cat, {}).get(n)
            pillar_scores[cat] = round(val, 1) if val is not None else None
        model["pillar_scores"] = pillar_scores

    # Rank
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified = [m for m in models if m["category_count"] >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if m["category_count"] < QUALIFICATION_MIN_PILLARS]

    ranked = sorted(qualified, key=today_score, reverse=True)
    for i, m in enumerate(ranked):
        m["display_rank"] = i + 1
        c = m["category_count"]
        m["tier"] = "verified" if c >= 7 else ("estimated" if c >= 4 else "minimal")

    for m in disqualified:
        m["display_rank"] = 0
        m["tier"] = "minimal"

    data["models"] = ranked + disqualified
    data["dates"]  = dates
    data["run_at"] = datetime.now().strftime("%-I:%M %p") + " CST"

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    duration = _time.time() - start_time
    write_status("success", ranked, source_summary, duration, total_sources_hit)

    ok = git_push(f"TR2 unified update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"âï¸ <b>Gimli | TR2 DDP done!</b>\n{TODAY}\n{len(qualified)} models")
    else:
        notify(f"âï¸ <b>Gimli | Push failed</b>\nJSON updated but push failed.\ncd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
