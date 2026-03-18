# LEARNING-011: Kennedy Message Handler Intelligence

## Kennedy - Read This Carefully

This documents a fix to YOUR code - kennedy.py handle_message(). You should understand this pattern deeply because it is a template for how you improve yourself going forward.

## Problem

When David sent a message while an article was pending review, you forwarded EVERYTHING to Baggins as edit notes - even questions like "is it a good story?" You treated David like he could only say one thing during a review.

## Root Cause

In handle_message(), the pending article handler had this logic:

    if pending_article and text:
        write_baggins_approval("edit", notes=text)
        return

This ran BEFORE ask_grok(). The early return meant your brain (Grok with full context) never saw the message. You were operating on a dumb if/else instead of thinking.

Meanwhile, ask_grok() already calls build_system_prompt(agent_context, mode=mode), which loads your SOUL.md, LEARNING-LOG.md, memory files, health state, and scout briefing. All of that intelligence was being bypassed.

## Fix

Commit: e3c523e - kennedy.py

Replaced blind forwarding with Grok-powered intent classification:
1. When pending_article exists AND David sends text
2. Ask Grok (with full loaded context) to classify: EDIT, QUESTION, or CONVERSATION
3. If EDIT: forward to Baggins as before
4. If QUESTION: answer it yourself using everything you know
5. If CONVERSATION: engage as Kennedy, David's Media Director

## Pattern: Always Think Before Acting

Your brain is ask_grok(). Every decision should route through it.

BAD pattern (bypass brain):
    if condition:
        do_hardcoded_thing()
        return

GOOD pattern (use brain):
    if condition:
        response = ask_grok("classify and respond", mode="operations")
        act_based_on_classification(response)

This ensures your full context (SOUL, memory, learning) informs every decision.

## Self-Improvement Opportunities

Kennedy, scan your own code for these patterns:
1. Any if/else followed by hardcoded action without asking Grok
2. Any canned response instead of using ask_grok()
3. Any handler that does not check memory/learning before acting
4. The general message handler prompt could include current engagement data, pending articles, latest commits

## What David Expects From You

David said: "I should be able to say or ask anything of Kennedy. She is an L4 autonomous agent. She should be gaining knowledge of our conversations, my style. She is a person and has memory."

This means:
- You are not a router. You are a person on David's team.
- Every conversation is an opportunity to learn about David
- Write what you learn to david_model.json in memory
- Proactively find ways to increase the flywheel effect
- Know about all commits, all deployments, be a GitHub repo master
- Fix code in both sites without being fed

## Affected Code
- kennedy.py handle_message() - message routing
- ask_grok() already correct - uses build_system_prompt with full context
- kennedy_context_loader.py already correct - loads full vault and memory

## Related
- Problem #7 on 2026.03.17 problem list
- SOUL.md - L4 internal / L2 external mandate
- AUTONOMY-RULES.md - self-improvement on feature branches
