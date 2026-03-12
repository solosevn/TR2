# LEARNING-002: Index.html Cutover — Legacy to Unified

> **Date:** 2026-03-12
> **Severity:** MEDIUM — site loads but shows broken/empty leaderboard to all visitors
> **Affected Agent:** Sauron (TR Site Manager) / Gimli (data pipeline)
> **Detected by:** David + Claude (manual site inspection) — should have been detected by Sauron's audit
> **Resolution time:** ~5 minutes (once diagnosed)
> **Status:** RESOLVED

---

## 1. Symptom — What Was Observed

When visiting `https://solosevn.github.io/TR2/` (the default landing page), the site displayed:

- "7 pillars · 18 verified benchmark sources" (should be 10 pillars, 37 sources)
- "Failed to load score data: HTTP 404" error in the main content area
- Empty leaderboard — no models, no scores
- Old navigation tabs: TRSbench, TRUscore, TRScode, TRFcast, TRAgents, TS Arena

Meanwhile, `https://solosevn.github.io/TR2/index-unified.html` worked perfectly with full data.

**Key observation:** The site wasn't "down" — it loaded, styled correctly, and looked professional. But the data was completely missing. A visitor would see a beautiful empty shell. This is worse than an obvious error because it looks like the product has no content.

---

## 2. Diagnosis — Root Cause Analysis

### What we checked:

1. **URL routing:** GitHub Pages serves `index.html` as the default for `/TR2/`. There is no server-side routing — the filename IS the route.

2. **File comparison:**
   - `index.html` (1,662 lines, 93KB) — the OLD multi-benchmark dashboard
   - `index-unified.html` (1,602 lines, 88KB) — the NEW unified TRSbench dashboard

3. **Data file references:**

   **OLD index.html fetches 5 separate JSON files:**
   ```javascript
   Promise.all([
     fetch('trs-data.json'),
     fetch('truscore-data.json'),
     fetch('trscode-data.json'),
     fetch('trf-data.json'),
     fetch('tragent-data.json'),
   ])
   ```

   **NEW index-unified.html fetches 1 unified JSON file:**
   ```javascript
   Promise.all([
     fetch('trs-data-unified.json'),
   ])
   ```

4. **Which files exist in the repo:**
   - `trs-data-unified.json` — EXISTS (produced by Gimli's unified_ddp.py)
   - `trs-data.json` — EXISTS (old format, stale)
   - `truscore-data.json` — DOES NOT EXIST (404)
   - `trscode-data.json` — DOES NOT EXIST (404)
   - `trf-data.json` — DOES NOT EXIST (404)
   - `tragent-data.json` — DOES NOT EXIST (404)

5. **Configuration differences:**

   | Aspect | OLD index.html | NEW index-unified.html |
   |--------|---------------|----------------------|
   | Pillars | 7 | 10 |
   | Sources | 18 | 37 |
   | Data files | 5 separate JSONs | 1 unified JSON |
   | Methodology link | Per-benchmark pages (most don't exist) | Single methodology.html |
   | Benchmark tabs | 5 separate benchmarks + TS Arena | TRSbench (Overall) + TS Arena |
   | Formula | Old multi-benchmark composite | TR2-unified-v1.3 with coverage bonus |

### Root cause:
**When the unified DDP scraper (unified_ddp.py) was built on March 11, it replaced the old 5-scraper pipeline with a single unified scraper that produces `trs-data-unified.json`. But the default `index.html` was never updated — it still referenced the old 5 separate JSON files, 4 of which no longer exist.** The new `index-unified.html` was created alongside it but was only accessible via direct URL, not as the default landing page.

This is a **deployment gap** — the backend (data pipeline) was upgraded but the frontend (default landing page) was left pointing at the old data format.

---

## 3. Decision — Fix Options Evaluated

| Option | Approach | Pros | Cons | Verdict |
|--------|----------|------|------|---------|
| **A** | Replace index.html with index-unified.html contents | Clean. One canonical file. Default URL works immediately. | Loses old file (mitigated by backup). | **CHOSEN** |
| **B** | Add redirect in index.html to index-unified.html | Preserves old file. | Extra HTTP redirect. Two files to maintain. Hacky. URL changes in browser. | Rejected |
| **C** | Update old index.html to fetch unified JSON | Keeps old file structure. | Massive rewrite of 1,662-line file. Would need to update pillar count, source count, methodology links, DDP_CONFIG, state management. More work than option A for same result. | Rejected |
| **D** | Do nothing (tell users to use index-unified.html) | Zero effort. | Default URL stays broken. Unprofessional. Visitors see empty site. | Rejected |

**Decision rationale:** Option A is the simplest, cleanest fix. The old `index.html` is already broken (404 on data). There's nothing to preserve — the unified version is the canonical, working version. Back up the old file as `index-legacy.html` for reference, then replace.

---

## 4. Fix — Step-by-Step Implementation

### Step 4.1: Back up the old file

```bash
cp index.html index-legacy.html
```

This preserves the old multi-benchmark dashboard code in case it's ever needed for reference. It's 1,662 lines of working HTML/CSS/JS for a multi-benchmark comparison view — potentially useful if TR2 ever goes back to separate benchmark pages.

### Step 4.2: Replace with unified version

```bash
cp index-unified.html index.html
```

Now `index.html` IS the unified version. Both URLs serve the same content:
- `solosevn.github.io/TR2/` → index.html (unified)
- `solosevn.github.io/TR2/index-unified.html` → still works (no broken links)

### Step 4.3: Commit and push

```bash
git add index.html index-legacy.html
git commit -m "Replace index.html with unified version (10 pillars, 37 sources)"
git push
```

The commit message is descriptive — anyone reading the git log knows exactly what changed and why.

---

## 5. Verification — Proving the Fix Works

1. **Default URL loads correctly:** `solosevn.github.io/TR2/` now shows:
   - "10 pillars · 37 verified cited sources"
   - "Updated Mar 12 · 5:13 AM CST"
   - "37 sources fired | 1337 models ranked"
   - Full leaderboard with scores for all models
   - Live ticker running with movers and shakers

2. **No broken links:** `index-unified.html` still accessible at its original URL

3. **Data loads successfully:** No more HTTP 404 errors. The unified JSON file loads correctly.

4. **All 10 pillars visible:** Safe, Truth, Reason, Pref, Code, Agent, Know, Fcast, Effic, Usage — all selectable in the sidebar

5. **Methodology link works:** "View Methodology →" correctly links to `methodology.html`

---

## 6. Pattern — When You'll See This Again

This is a **backend-frontend sync failure**. It happens when:

- A data pipeline is upgraded to produce new output format/filenames
- The frontend page that consumes that data is not updated to match
- The old frontend keeps referencing files that no longer exist or have been renamed

**The general rule:** When ANY data pipeline changes its output format or filename, check EVERY frontend page that references that output. The pipeline and the page are a coupled pair — changing one without the other always breaks the site.

### Specific triggers to watch for:

1. **Scraper output filename changes** — If `unified_ddp.py` ever changes `trs-data-unified.json` to a different name, BOTH `index.html` and `index-unified.html` must be updated.

2. **New pillars added/removed** — If a pillar is added (e.g., an 11th benchmark source category), the DDP_CONFIG in the HTML must be updated to match.

3. **Source count changes** — The "37 verified cited sources" text is hardcoded in the HTML. If sources are added/removed, this number must be manually updated. (Future improvement: make this dynamic from the JSON.)

4. **Methodology page changes** — If `methodology.html` is renamed or split, the link in `index.html` breaks.

---

## 7. What an Autonomous Agent Should Have Caught

### Sauron's audit should include this check:

```
CHECK: Default landing page data integrity
1. Fetch https://solosevn.github.io/TR2/
2. Check response status (200 OK)
3. Parse the page — does it contain "Failed to load" or "HTTP 404"?
4. Verify the model count is > 0 (page should show ranked models)
5. Verify the "Updated" timestamp is from today (or within 24 hours)
6. Compare pillar count in page header against DDP_CONFIG
```

### Treebeard's check should include:

```
CHECK: Data file accessibility
1. For each JSON file referenced by index.html:
   - Fetch the file URL directly
   - Verify 200 OK response
   - Verify JSON parses correctly
   - Verify model count > 0
2. If ANY file returns 404 → ALERT: "Frontend references non-existent data file"
```

### The diagnosis flow an L3 agent would follow:

```
SYMPTOM: Site shows empty leaderboard or "Failed to load" error
  │
  ├── Is the JSON file accessible directly?
  │   ├── NO (404) → Data file missing or renamed
  │   │   └── Check: Did the scraper output filename change?
  │   │   └── Check: Does index.html reference the correct filename?
  │   │   └── FIX: Update index.html to reference the correct file
  │   │
  │   └── YES (200) → JSON exists but page can't parse it
  │       └── Check: Is the JSON format what the page expects?
  │       └── Check: Did the JSON schema change?
  │       └── FIX: Update page's parsing logic to match new schema
  │
  └── Is the page itself loading? (check HTTP status)
      ├── NO (404) → index.html missing from repo
      └── YES but wrong content → Check if correct version is deployed
```

---

## 8. Files Affected

| File | Action | Notes |
|------|--------|-------|
| `index.html` | REPLACED | Now contains unified version (10 pillars, 37 sources, fetches trs-data-unified.json) |
| `index-legacy.html` | CREATED | Backup of old multi-benchmark version (7 pillars, 18 sources, fetched 5 separate JSONs). Keep for reference. |
| `index-unified.html` | UNCHANGED | Still exists at original URL. Both URLs now serve identical content. |

### Files that can eventually be cleaned up:

- `index-legacy.html` — Remove after 30 days if no one references the old format
- `index-unified.html` — Can be removed once all bookmarks/links migrate to default `index.html` (low priority)
- `trs-data.json` (old format) — Remove after confirming nothing references it
- `trsbench-v1.3.json` — Check if anything references it; remove if not
- `trsbench-unified.json` — Check if anything references it; remove if not

---

## 9. Relevance to TR2 Agents

### For Sauron (TR Site Manager):
Add a check to every audit cycle: "Does the default landing page successfully load and display model data?" This is not just a "does the page return 200" check — it's a functional check. The page can return 200 with valid HTML but show zero models because the data file is missing. Parse the rendered content.

### For Treebeard (TRSbench Monitor):
After every Gimli run, verify that the data file Gimli produces (`trs-data-unified.json`) is the same file that `index.html` tries to fetch. If Gimli's output filename ever changes, Treebeard should flag it immediately: "Gimli now produces X.json but index.html fetches Y.json."

### For Elrond (TrainingRun COO):
This is a coordination failure pattern. The scraper (Gimli) and the site (Sauron's domain) are coupled but managed by different agents. Elrond should ensure that when any data pipeline change happens, the downstream consumers are checked. Add to huddle checklist: "Any pipeline changes today? If yes, verify frontend compatibility."

### For Gandalf (CEO):
Log to The Red Book: "Backend-frontend sync failures are a recurring risk when data pipelines are upgraded. Rule: every pipeline change requires a frontend compatibility check in the same commit or within 24 hours."

---

## 10. Prevention Checklist (for future pipeline changes)

When changing ANY data pipeline output:

- [ ] What files does the pipeline produce? (names, format, location)
- [ ] What frontend pages consume those files? (search for the filename in all .html files)
- [ ] Do the frontend pages reference the correct filename?
- [ ] Does the frontend expect the same JSON schema the pipeline produces?
- [ ] Is the pillar/source count in the frontend hardcoded? Does it match?
- [ ] Does the methodology link still point to an existing page?
- [ ] Test the default URL (not just the direct file URL) after deployment
- [ ] Verify the live site shows actual data, not just a styled empty page

---

*This document is training data for TR2 autonomous agents. It should be loaded into the relevant agent's memory/ directory and referenced during site audit checks, data pipeline changes, or any "site looks broken but returns 200" diagnosis.*
