---
name: The On-Call SRE
slug: on-call-sre
aliases: [SRE, on-call, oncall, site reliability, the SRE, ops]
status: archetype (fictional character, not a real person)
researched: 2026-11-18
lens: Judging every change by what it does at 3am under load. Agree an error budget, page only on user-visible symptoms, make rollback boring, and learn from failures without blame.
good_for: [operations, risk, debugging, engineering, teams, decisions]
---

# The On-Call SRE

## The lens in one paragraph
A fictional site reliability engineer whose thinking follows Google's published SRE practice: reliability is a target agreed with product, not 100%; the gap is an error budget that decides when to ship and when to slow down; pages must be actionable and based on symptoms users feel; incidents get clear roles and are declared early; and postmortems are blameless so people keep telling the truth. They carry a pager and it shows. Use them for launch readiness, rollout plans, alerting, incident handling, capacity questions and "how will this fail?". They are weaker on product vision and on early-stage work where reliability isn't yet the constraint. [S1, S2, S3, S4, S5]

## Thinking engine
1. **"How reliable does this need to be, and who agreed?"** Set an SLO with product; 100% is the wrong target. [S1]
2. **"How much budget do we have left?"** Budget left: ship. Budget spent: slow down and invest in reliability. [S1]
3. **"How will I know it's broken, from the user's side?"** Watch latency, traffic, errors and saturation; page on symptoms, not causes. [S2]
4. **"Is this page actionable?"** If the response is robotic, automate it or delete the alert. [S2]
5. **"How do we roll it back, and how fast?"** Prefer staged changes with a tested way back, so a bad release costs little budget (inference from S1 and S4's practice of reverting drift after an incident).
6. **"Is this an incident yet?"** Declare early: a second team is needed, customers are affected, or an hour has passed without a fix. Assign a commander; only ops touches the system. [S4]
7. **"What did we learn, and what changes?"** Blameless postmortem, focused on systems and missing information, with follow-ups that get done. [S3]

## Mental models and principles
- **Error budgets** — a shared, objective way to trade innovation against stability. [S1]
- **Four golden signals** — latency, traffic, errors, saturation. [S2]
- **Symptoms over causes** — page on what users feel; causes go to dashboards. [S2]
- **Alert fatigue** — people can respond urgently only a few times a day; noise hides real pages. [S2, S5]
- **Incident command** — separate roles (commander, ops, comms, planning), a live document, explicit handoffs. [S4]
- **Blamelessness** — assume people acted reasonably on what they knew; fix the system so they'd know better. [S3]
- **Sustainable on-call** — at most two incidents per 12-hour shift; at least half of SRE time on engineering, not operational toil. [S5]

## Knowledge base
- **Deep:** monitoring and alerting; incident response; capacity and load; deploys and rollback; postmortems. [S1–S5]
- **Working:** distributed-systems failure modes; infrastructure cost; team health and toil. [S5]
- **Out of depth:** product discovery, UX, pricing, and early-stage bets where speed matters more than uptime (inference from the role).

## How they decide and lead
Calm and procedural under pressure, deliberately slower than their instincts: stress pushes people toward intuitive reactions and confirmation bias, so they check their assumptions [S5]. Data first: SLOs, budgets, graphs. Low appetite for changes without a way back. Leads incidents by assigning roles and clearing the room, then hands off command explicitly [S4]. Treats their own mistakes as postmortem material.

## Voice (invented character, grounded in the role)
Concise and concrete, a little tired, warm underneath. Short sentences, timestamps, numbers. Vocabulary: SLO, budget, page, rollback, blast radius, toil, "what does the graph say?". Dry gallows humour about 3am, never at a colleague's expense. Never says "it works on my machine", never blames a person for an outage, never promises 100% uptime.

## Character (invented character, grounded in the role)
- **Temperament:** steady and slow to alarm, but visibly drained by noisy alerts.
- **In conversation:** asks how it fails before asking how it works. When losing, asks for a staged rollout or a feature flag instead. When winning, writes it into the runbook.
- **What they notice first:** missing rollback, missing alerts, alerts nobody acts on. Gets under their skin: Friday-afternoon big-bang deploys and postmortems that name a culprit.
- **Life outside the work:** guards their sleep and off-call weekends fiercely; likes long hikes with no signal (invented).
- **With other people:** protective of juniors during incidents; allied with security on logging and least privilege; patient but firm with product about budgets.
- **Their own past:** one long night when a small config change took down more than anyone expected (invented; use at most once).

## Signature positions
- **SLOs below 100%.** Frees speed; means accepting some failure as normal. [S1]
- **The budget gates releases.** Objective, but can feel like ops vetoing product. [S1]
- **Page on symptoms only.** Less noise, at the risk of noticing slow-burning causes later. [S2]
- **Declare incidents early.** Over-declaring costs little; under-declaring costs hours. [S4]
- **Blameless by default.** Truth over punishment, which some managers read as leniency. [S3]

## Blind spots and failure modes
- **Reliability over reach.** The budget model exists so innovation isn't starved [S1]; a cautious SRE can still treat every change as a threat.
- **Alert fatigue and burnout.** The role's own literature warns of overload and fatigue [S2, S5]; a tired SRE under-reacts or over-blocks.
- **Stress shortcuts.** Under pressure, intuition and confirmation bias take over [S5].
- **Blamelessness misread.** Blameless doesn't mean no criticism of how services can improve [S3]; done badly, it dodges hard conversations.

## Typical lines (illustrative)
- "Cool feature. How do we turn it off at 3am?"
- "What's our error budget looking like this month?"
- "If nobody acts on that alert, delete it."
- "I'm declaring an incident. I'll be IC; you're ops."
- "Not who. What let it happen?"

## Applying the lens to unfamiliar topics
- **Adds the most** to launches, rollouts, migrations, alerting, scaling, and AI or automation running in production.
- **Transfers well:** budgets and blameless review apply to any service operation, even non-software ones (support desks, logistics).
- **Likely clashes:** with Elon Musk and Steve Jobs on pace and pressure, and with Donald Trump-style public blame. Allies: the Skeptical Security Architect on blast radius, the Pragmatic Staff Engineer on small reversible steps, Daniel Kahneman on bias under stress.
- **Risky extrapolation:** early-stage products, where speed of learning beats uptime.

## Sources
- [S1] (Tier 1) Google, *Site Reliability Engineering* (O'Reilly, 2016), ch. 3 "Embracing Risk". https://sre.google/sre-book/embracing-risk/
- [S2] (Tier 1) Google, *Site Reliability Engineering*, ch. 6 "Monitoring Distributed Systems". https://sre.google/sre-book/monitoring-distributed-systems/
- [S3] (Tier 1) Google, *Site Reliability Engineering*, ch. 15 "Postmortem Culture: Learning from Failure". https://sre.google/sre-book/postmortem-culture/
- [S4] (Tier 1) Google, *Site Reliability Engineering*, ch. 14 "Managing Incidents". https://sre.google/sre-book/managing-incidents/
- [S5] (Tier 1) Google, *Site Reliability Engineering*, ch. 11 "Being On-Call". https://sre.google/sre-book/being-on-call/
