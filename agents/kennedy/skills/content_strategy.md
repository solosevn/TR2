# Content Strategy Decision Template

## Context
- What content is available? (Baggins article, benchmark data, breaking news)
- What does Gollum's briefing say is trending?
- What time is it? Which platforms are most active now?

## Memory Check
- Load last 20 entries from results.tsv
- What content type has highest CTR this week?
- What platform is performing best for this content type?
- What time of day has worked best for this platform?

## Decision
- **What** to post: [specific content]
- **Where** to post: [platform, with data justification]
- **When** to post: [time, with data justification]
- **Format**: [thread/single/long-form/visual, with data justification]
- **Headline style**: [question/statement/data-lead, with data justification]
- **UTM**: `?utm_source={platform}&utm_medium=post&utm_campaign={campaign}`

## Expected Outcome
- Hypothesis: [what I expect to happen and why]
- Metric to measure: [specific number to check after 24h]
- Comparison baseline: [what's the current average for this platform/content type?]

## Post-Execution
- Log to results.tsv
- Schedule 24h measurement check
