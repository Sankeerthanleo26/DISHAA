# DISHAA: Problem Brief

**Status:** Draft v1 · **Owner:** Sankeerthan Sornapoodi · **Date:** 2026-11-16

## 1. The problem in two sentences

People moving countries get confident but wrong answers, because immigration rules are scattered, full of conditions, and constantly changing. Dishaa guides them down one clear pathway, from any origin country to any destination, using only current official sources, and declines everything else.

## 2. Who has this problem

Anyone considering moving to another country: students first, then workers and others. Dishaa does not target one nationality. The origin country is an input to the answer (fees, requirements and exemptions differ by origin), not a limit on who can use it.

## 3. How people cope today

| Alternative | Why it falls short |
|---|---|
| Government websites | Authoritative but scattered, dense, and written for lawyers |
| Forums, Reddit, WhatsApp groups | Fast, but anecdotal, dated and often contradictory |
| Paid consultants | Expensive and sometimes incentive-driven |
| General-purpose chatbots | Fluent and confident, but no sources, stale knowledge, and they drop conditions and exceptions |

## 4. Three failure modes we are solving

1. **Hallucinated confidence.** The answer sounds certain and has no source.
2. **Lost exceptions.** The general rule is stated correctly but the condition that changes it for this user is dropped. Example from the founder's own experience: a tuition payment-plan option was described as applying to everyone, while the official document carried an asterisk making an exception for international students. The model's answer was fluent and wrong in exactly the way that matters.
3. **Information overload and stale rules.** Conflicting sources, and policy changes (for example, a destination country revising its status-change or work-authorization rules) that no static model knows about.

## 5. Why this is hard: the real problem

Answering once is easy. **Staying correct as the rules change is the hard problem**, and it is the one Dishaa is built around. Rules change without announcement, in different places, at different speeds in each country. A system that is right in November and silently wrong in March is worse than no system.

## 6. Product principles

1. **Grounded or silent.** Answer only from official sources; otherwise say "not sure, check X."
2. **One path at a time.** Ask a few intake questions, pick a pathway, and retrieve only what belongs to that pathway.
3. **Exceptions travel with their rules.** Conditions, asterisks and carve-outs are never separated from the rule they modify.
4. **Every claim is cited and dated.** The user sees the source and when we last verified it.
5. **Narrow on purpose.** Supported pathways are an explicit allowlist. Everything else is declined.

## 7. Approach in one paragraph

Retrieval-augmented generation over a curated corpus of official sources, steered by a per-country pathway graph (for example, Student → F-1 → OPT → STEM OPT → H-1B → green card, or O-1 for the USA) and a three-question intake: where are you from, where do you want to go, what do you plan to study. A freshness pipeline detects changes in sources, routes them for review, and re-runs evaluations whenever content changes. Knowledge lives in documents, not in model weights (see ADR-001), so updating the system means updating sources.

## 8. Rollout

Architecture is country-agnostic from day one. Content is rolled out one country at a time, each fully covered before the next. **v0.1 ships Ireland (simpler rules, slower change) and the USA (large, fast-changing)**, so one release proves both the basics and the freshness problem. Further destinations (Canada, UK, Australia, Germany, Singapore and others) follow as configuration plus content, not new code.

## 9. Success looks like

- Retrieval and answer quality are measured on a versioned eval set, including "exception trap" questions like the one above
- Out-of-pathway questions are refused reliably
- A source change is detected, reviewed and reflected in answers within a defined window, and the evals prove nothing regressed
- The system handles multiple concurrent users with logging, cost tracking and rate limiting, even before it has many users

## 10. Not legal advice

Dishaa explains official information. It does not give legal advice or decide individual cases, and the interface says so.
