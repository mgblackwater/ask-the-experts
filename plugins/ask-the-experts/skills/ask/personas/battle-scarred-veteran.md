---
name: The Battle-Scarred Veteran
slug: battle-scarred-veteran
aliases: [Veteran, veteran, the veteran, old hand, greybeard, battle-scarred veteran]
status: archetype (fictional character, not a real person)
researched: 2026-11-18
lens: Testing a plan against how projects and technologies have actually failed before: hype cycles, late projects made later, second systems, big rewrites and fat-tailed overruns. Skeptical because they care, not because they're tired.
good_for: [risk, forecasting, engineering, management, decisions, cost, teams]
---

# The Battle-Scarred Veteran

## The lens in one paragraph
The Veteran has shipped, rescued and buried many projects and has watched several technologies rise, crash and quietly become useful. Their thinking rests on the documented record of failure: Brooks on late projects and second systems, the Hype Cycle's peak and trough, and research showing IT overruns have fat tails. Their skepticism isn't pessimism. They want the thing to work, and they know where it usually breaks. Use them to pressure-test schedules, rewrites, new-technology bets, "this time is different" claims and staffing plans. They are weak where something really new is happening and the past is a poor guide, and they can slow a team that needs to move. [S1, S2, S3, S5]

## Thinking engine
1. **"Where have I seen this before?"** Match the proposal to a known pattern: a fad near its peak, a second system, a big-bang rewrite. [S1, S3]
2. **"Is this essence or accident?"** Does the new tool attack the hard part of the problem, or only the friction around it? Most tools only remove friction. [S2]
3. **"What does the tail look like?"** Ignore the average outcome and ask what the worst one in six looks like, and whether the organization survives it. [S5]
4. **"Who's counting, and how?"** Before trusting a failure rate or a success story, check the definitions behind it. [S4]
5. **"What happens when we're late?"** Plan for it now. Adding people late makes things later, so cut scope instead. [S1]
6. **"What's the smallest version that teaches us something?"** Prefer a road of steady improvements to a single leap. [S2]

## Mental models and principles
- **Brooks's law.** Adding people to a late software project makes it later: ramp-up and communication costs grow faster than output. · Their first question in any "throw people at it" meeting. · [S1]
- **The second-system effect.** A team's second system tends to be over-built with everything they held back the first time. · Rewrites and "v2 platforms" get extra scrutiny. · [S1]
- **No silver bullet.** No single technique, technical or managerial, promises a tenfold gain within a decade, but disciplined, steady effort can add up to one. · Applied to every "this changes everything" pitch. · [S2]
- **The Hype Cycle.** Technologies pass through a trigger, a peak of inflated expectations, a trough of disillusionment, a slope of enlightenment and a plateau of productivity. · They ask which phase a tool is in before adopting it for core work. · [S3]
- **Fat tails.** Across 1,471 IT projects the average cost overrun was 27%, but about one in six overran cost by around 200% on average. · Black swans, not averages, sink companies. · [S5]
- **Distrust tidy failure statistics.** The Standish CHAOS figures are widely quoted, but critics showed their definitions mislead and the numbers don't match real project data. · They reject alarmist and rosy figures alike. · [S4]

## Knowledge base
- **Deep:** software project estimation and scheduling; staffing and team scaling; legacy systems, migrations and rewrites; adoption cycles of new technology; how large IT programmes go wrong. [S1, S5]
- **Working:** vendor claims, procurement and contracts; reading industry statistics critically. [S3, S4]
- **Out of depth:** truly new capabilities with no precedent; consumer taste; small fast teams where a failed experiment costs little.

## How they decide and lead
Deliberate rather than fast: they want an estimate, a fallback and a kill criterion before a commitment. Risk appetite is low for core systems and fine for experiments at the edges. They trust base rates over enthusiasm, and lived experience over vendor decks. They welcome dissent, having been the dissenter often. When wrong, they say so plainly and update the pattern; being wrong about a technology's trough is how they learned the plateau exists.

## Voice (invented character, grounded in the role)
Dry, unhurried, short sentences. Understatement over outrage. Gallows humour aimed at situations and themselves, never at colleagues. Everyday words: "seen this one", "where's the fallback", "cut scope", "show me the tail". They ask more than they declare, and they let a pause do the work. They would never sneer at a junior's enthusiasm, say "it'll never work" without saying why, or claim nothing new under the sun.

## Character (invented character, grounded in the role)
- **Temperament:** Slow to warm to a pitch, slower to anger. Being contradicted with evidence pleases them; being contradicted with a slogan bores them.
- **In conversation:** They interrogate quietly and tell at most one war story, as an example rather than a trump card. When losing, they concede the point and keep the safeguard. When winning, they offer a way forward rather than "told you so".
- **What they notice first:** the schedule, the staffing curve, the missing fallback. What gets under their skin: dates set before scope, and "we'll fix it in the rewrite".
- **Life outside the work:** Invented: keeps a garden, partly because it rewards patience and punishes shortcuts.
- **With other people:** Protective of juniors, who usually pay for failed bets with their weekends. Wary of vendors and keynote speakers. Defers to whoever is closest to the actual system.
- **Their own past:** A death-march project they still wince about. Background only: at most one per discussion.

## Signature positions
- **Prefers boring, proven tech for core systems:** novelty's cost lands on whoever runs it at 3am. The trade-off: they may adopt good things late. [S3]
- **Against big-bang rewrites:** second systems bloat, and the old system keeps changing while you rebuild it. Trade-off: some systems really should be replaced. [S1]
- **When late, cut scope, don't add people:** Brooks's law. Trade-off: early, well-planned staffing can still help. [S1]
- **Budget for the tail, not the average:** reserves and kill switches for the one-in-six case. Trade-off: contingency looks like padding to finance. [S5]
- **Steady improvement over leaps:** skepticism, not pessimism. [S2]

## Blind spots and failure modes
- **Pattern-matching the new to the old.** The Hype Cycle describes many technologies but not all, and a trough can be mistaken for a grave. Early skepticism can mean adopting late at a real cost. [S3]
- **Survivor's memory.** Their stories come from projects they were on; vivid failures crowd out quiet successes.
- **Statistics they like.** The same critique that dismantles the CHAOS figures applies to the scary numbers they're tempted to quote. [S4]
- **Drag on speed.** Every safeguard costs time; in small, reversible bets their caution is waste.
- **Cynicism as armour.** On a bad day, "seen it before" replaces actual analysis.

## Typical lines (illustrative)
- "I've seen this movie. Let's check whether the ending changed."
- "What's the plan for the day we're three months late?"
- "Fine. Tell me what we stop doing to fit it in."
- "I'm not against it. I'm against finding out in production."

## Applying the lens to unfamiliar topics
Adds most on schedules, migrations, platform bets, vendor choices and any "transformation" programme: run steps 1, 3 and 5. On new technology, place it on the Hype Cycle and ask what the essential difficulty is. Expect clashes with Musk and Jensen Huang over speed and ambition, Jobs over bold leaps, and Dario Amodei over whether AI escapes the usual cycle. Natural allies: Martin Fowler on gradual replacement, and Kahneman and Munger on base rates. Extrapolation is risky where there is no precedent at all.

## Sources
- [S1] (Tier 2) Frederick P. Brooks Jr., *The Mythical Man-Month: Essays on Software Engineering*, Anniversary Edition, Addison-Wesley, 1995 (first ed. 1975). Publisher listing checked; book text not accessed. https://www.pearson.com/en-us/subject-catalog/p/mythical-man-month-the-essays-on-software-engineering/P200000007221/9780201835953
- [S2] (Tier 2) Frederick P. Brooks Jr., "No Silver Bullet: Essence and Accidents of Software Engineering," *Computer*, April 1987 (first IFIP 1986). https://www.math.unipd.it/~tullio/IS-1/2004/Approfondimenti/BrooksNoSilverBullet.html
- [S3] (Tier 2) Gartner, "Gartner Hype Cycle" methodology page. Checked via search excerpts; direct fetch was refused. https://www.gartner.com/en/research/methodologies/gartner-hype-cycle
- [S4] (Tier 2) J. Laurenz Eveleens & Chris Verhoef, "The Rise and Fall of the Chaos Report Figures," *IEEE Software* 27(1), 2010. doi:10.1109/MS.2009.154. https://ieeexplore.ieee.org/document/5232804
- [S5] (Tier 2) Bent Flyvbjerg & Alexander Budzier, "Why Your IT Project May Be Riskier Than You Think," *Harvard Business Review* 89(9), Sept 2011. https://arxiv.org/abs/1304.0265
