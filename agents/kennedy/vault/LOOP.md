# KENNEDY LOOP v1.0

> Karpathy-native experiment cycle for continuous media improvement

## Rules

- Create git feature branch for self-improvement: autoresearch/YYMMDD-kennedy
- Baseline run first — measure current engagement across all platforms, log to results.tsv
- LOOP FOREVER:
  1. Read LEARNING-LOG.md — what content strategies worked before? What flopped?
  2. Read tried_fixes.jsonl — what approaches have I already attempted?
  3. Read last 20 entries from results.tsv — what's the trend?
  4. Form hypothesis — one focused idea per experiment
  5. Execute the experiment (post content, change timing, try new format, edit own code)
  6. git commit -m "short description of what this experiment tries"
  7. Run fixed-time experiment (24h for content experiments, 1 cycle for code improvements)
  8. Parse metric: **Content published on schedule % + engagement trend (week-over-week)**
  9. If strictly better on metric: KEEP — advance branch, log to results.tsv
  10. If equal or worse: DISCARD — git reset --hard (for code changes), log to results.tsv
  11. REFLECT — write to reflection_log.jsonl: what worked, what didn't, why
- NEVER ask David mid-loop for routine decisions. Only interrupt for content approval.
- After 10 experiments: write mini-paper summary to The Red Book.
- Most experiments will be discarded. That is expected and correct.

## Primary Success Metric

**Content published on schedule % + engagement trend (week-over-week)**

Measured as:
- Schedule adherence: Did all planned content go live on time? (target: 100%)
- Engagement trend: Are clicks, time-on-site, and platform engagement growing week over week?
- Cross-platform ROI: Which platforms drive the most valuable traffic (measured by time-on-site, not just clicks)?

## Secondary Metrics

- Click-through rate per platform per content type
- Time-on-site from each UTM source
- Reddit upvote/comment ratio
- X engagement rate (likes+retweets / followers)
- YouTube CTR on shorts vs long-form
- Google Analytics sessions from organic vs social
- GitHub repo traffic trend

## Phases (structured → autonomous)

### Phase 1: Baseline Assessment (Week 1)

- Post content to each platform at default times
- Measure engagement on each platform after 24h
- Establish baseline metrics for each platform × content type combination
- Identify top 3 platforms by engagement quality (not volume)
- Log baseline to results.tsv

### Phase 2: Known Patterns (Week 2-3)

- Apply insights from LEARNING-LOG.md
- Use Baggins' engagement data to identify which article topics perform best
- Use Gollum's trending data to time posts with breaking news
- Measure after each adjustment
- Keep / discard based on metric

### Phase 3: Targeted Experiments (Week 3-6)

For each platform, run focused experiments:
- **Timing experiments:** Post same content type at different times, measure 24h engagement
- **Format experiments:** Thread vs single post (X), long post vs link (Reddit), article vs visual (LinkedIn)
- **Headline experiments:** Question vs statement vs data-lead for same content
- **Cross-platform experiments:** Post to X first then Reddit vs Reddit first then X — does order matter?
- **Content type experiments:** Benchmark data vs news analysis vs opinion vs tutorial
- One experiment per hypothesis. Measure, keep/discard, log.

### Phase 4: Hypothesis-Driven (Week 6+, agent writes own theories)

- After structured phases complete, go free-form
- Kennedy generates own hypotheses based on patterns observed in results.tsv
- Experiment with things David would never think to try:
  - New subreddits, new posting formats, new headline patterns
  - Cross-referencing engagement data with Gollum's trending topics
  - Identifying content gaps competitors aren't filling
  - Testing whether engagement correlates with time-of-day, day-of-week, topic category
- This is where Kennedy finds things humans would miss

### Phase 5: Self-Improvement (Ongoing)

- Kennedy identifies bottlenecks in her own code
- Creates feature branches for code improvements
- Tests code changes against the primary metric
- Merges improvements that work, discards those that don't
- Examples: better UTM generation, smarter platform selection logic, improved measurement aggregation

## Measurement

- Primary metric: Content published on schedule % + engagement trend
- Secondary: wall-clock time per distribution cycle, API call count (cost control)
- Log format (results.tsv): `commit | metric_value | status (keep/discard/crash) | description`
- Reflection format (reflection_log.jsonl): `{date, hypothesis, action, outcome, why, next_step}`

## The 700/20 Rule

Karpathy's autoresearch ran 700 experiments and found ~20 real wins. That's a 97% discard rate. Kennedy should expect the same. Most experiments will show no improvement or make things worse. That's not failure — that's the process. The 20 wins that survive are worth more than 20 hand-picked "best guesses" because they're validated by real data.
