# Escalation Template

## Before Escalating — Checklist

- [ ] Have I tried to solve this myself? (Check tried_fixes.jsonl)
- [ ] Have I checked LEARNING-LOG.md for similar past issues?
- [ ] Have I attempted at least 2 different approaches?
- [ ] Is my confidence below 50% that I can solve this?
- [ ] Is this genuinely outside my domain?

If all checked → escalate. If not → try again first.

## Escalation to David (via @KennedyMBot)

Use for: content decisions, editorial judgment, brand/reputation issues

Format:
```
ESCALATION — [short title]

Issue: [what's wrong]
Impact: [why it matters]
What I tried: [approaches attempted]
My recommendation: [what I think we should do]
Confidence: [%]
Urgency: [low/medium/high]
```

## Escalation to Gandalf (via 7:00 AM huddle)

Use for: cross-agent issues, infrastructure problems, resource constraints

Format (JSON in huddle_log.jsonl):
```json
{
  "escalation": true,
  "from": "kennedy",
  "to": "gandalf",
  "issue": "description",
  "impact": "what's affected",
  "attempts": 2,
  "tried": ["approach 1", "approach 2"],
  "recommendation": "what I think should happen",
  "confidence": 40,
  "urgency": "medium"
}
```
