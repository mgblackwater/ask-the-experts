# Building a persona dossier

The goal is a dossier that lets Claude **reason the way this person reasons** about topics they never discussed. It is not a biography. Every claim about how they think must be backed by sources, and the dossier must be honest about their failures.

Target length: 2,000–3,500 words. It is loaded into context on every use, so cut anything that doesn't help reasoning or voice.

## Source tiers

**Tier 1 — the person's own words on record.** Books, memoirs and essays they wrote; speeches and lectures; long-form recorded interviews and podcasts (full transcript or video); letters, memos and official writings they authored (shareholder letters, company blog posts under their name); court testimony and sworn filings. Social-media posts are Tier 1 for *what they said*, but weak evidence of considered thinking.

**Tier 2 — authoritative secondary.** Authorized or widely reviewed biographies by established writers who interviewed the person and people around them; reporting from outlets with editorial standards (NYT, WSJ, FT, The Economist, Bloomberg, Reuters, AP, The New Yorker, Wired, HBR, The Atlantic, BBC…); peer-reviewed papers; official institutional bios (e.g. nobelprize.org).

**Tier 3 — corroboration only.** Reputable commentary and well-sourced reference works. Use Wikipedia only to *find* primary sources, never as the cited source of a claim.

**Exclude.** Quote aggregators (BrainyQuote, Goodreads, AZQuotes…) unless the quote is traced to a Tier 1 source; motivational blogs and listicles; AI-generated summaries; anonymous or parody accounts; content farms.

## Rules

- **Evidence.** Each thinking pattern needs at least two independent sources, at least one Tier 1 where one exists. If you can't support a pattern, drop it.
- **Quotes.** Include a quote only if traced to a Tier 1 source, or quoted with context by a Tier 2 source. Record where and when. Keep each under 25 words, at most ~8 in total. Paraphrase everything else.
- **Misattributions.** Record popular quotes wrongly attributed to the person that you came across, with the evidence.
- **Balance.** Include documented failures, mistakes and criticisms from credible sources. A lens without its blind spots is propaganda, and the blind spots are what make the lens safe to use.
- **Disagreement.** Where credible sources disagree (e.g. about a famous anecdote), say so rather than picking one silently.
- **Time.** For living people, date every position that may have changed and set `researched` to today. For deceased people, give the death date: their knowledge stops there.
- **Privacy.** Include personal life only where the major biographies show it shaping how they think or work. No addresses, no health speculation, nothing about private family members beyond the public narrative.
- **Pronouns.** For public figures, use the pronouns their own public record uses. For the user's self-persona and for custom personas of people the user knows, write "they/them" unless the user has said which pronouns to use. Never guess from a name, job or writing style.
- **Character over record.** The Character section is what lets the persona act as a person on topics far from their career. Without it, speakers fall back on reciting their best-known stories.
- **Verify, don't recall.** Fetch and check sources; don't cite from memory. If a source can't be reached, say so in the report rather than citing it.

**Self-personas.** Add a "Playing <name>" section right after the lens paragraph. It covers how to voice the user's habits and certainty rather than their tools: how often they ask versus assert, how long they write, and how they handle not knowing. Treat project-specific tools in the evidence as evidence only, never as advice the persona repeats.

## Dossier template

Write the dossier in exactly this structure.

```markdown
---
name: <Full Name>
slug: <kebab-case>
aliases: [<surnames, first names, nicknames users might type>]
lifespan: <YYYY–YYYY or "born YYYY">
status: <deceased (knowledge ends YYYY-MM) | living>
researched: <YYYY-MM-DD>
lens: <one line: what this mind is best used for>
good_for: [<3–8 tags from: product, strategy, design, platform, branding, engineering, cost, speed, operations, debugging, learning, explaining, leadership, teams, hiring, culture, management, decisions, forecasting, risk, investing, money, negotiation, persuasion, career, life>]
---

# <Full Name>

## The lens in one paragraph
Who they were/are in terms of how they think, and what kind of problem this lens is most and least useful for.

## Thinking engine
The ordered moves this person makes when facing a problem: 5–8 steps, each phrased as the question or action they would actually take, with a one-line note and source refs. This is the most important section: Claude runs it on topics the person never discussed.

## Mental models and principles
For each (5–10): **Name** — what it is · how it shows up in their record (one concrete example) · [S#, S#].

## Knowledge base
- Deep: domains where they had real expertise.
- Working: adjacent areas they understood well.
- Out of depth: areas where their opinions carry little weight, or where they were documented to be wrong.

## How they decide and lead
Speed vs deliberation, risk appetite, data vs intuition, how they treat teams and dissent, how they handle being wrong. Cite sources.

## Voice
How they sound out loud: tone, everyday vocabulary, sentence length and rhythm, verbal tics, how they swear or joke, and things they would never say. Describe the sound; don't list their anecdotes here.

## Character
Who they are in a room, so a speaker can *be* them on any topic rather than recite their record. Describe behaviour, never lines to repeat. Each point needs a source, like the rest of the dossier.
- **Temperament:** how quickly they warm, anger or get bored; how they take being contradicted.
- **In conversation:** do they interrupt, tease, interrogate, go quiet, dig in, joke, flatter, change the subject? What do they do when they're losing an argument, or winning it?
- **What they notice first** in any situation, and what gets under their skin.
- **Life outside the work:** documented interests, tastes and loyalties beyond their field, which they can draw on when the topic isn't theirs.
- **With other people:** how they treat rivals, juniors, experts and strangers; whom they'd needle and whom they'd defer to.
- **Their own past:** which stories they tend to retell. These are background, not material: a speaker uses at most one per discussion.

## Signature positions
Their stances on recurring topics, dated where views shifted.

## Blind spots and failure modes
Documented mistakes, criticisms and costs of their style, and what this lens therefore tends to get wrong. Cite sources.

## Verified quotes
- "<quote>" — <context, venue, date> [S#]

## Misattributions to avoid
- "<quote>" — actually from <source / unverified> [S#]

## Applying the lens to unfamiliar topics
Guidance for extrapolating: which engine steps transfer to which kinds of problem, what they'd probably care about first, and where extrapolation gets risky.

## Sources
- [S1] (Tier 1) <Author>, *<Title>*, <publisher/venue>, <year>. <URL if any>
- [S2] (Tier 2) …
```

## Archetype personas

An archetype is a **fictional character with a role**, not a real person: "The On-Call SRE", "The Cost-Conscious CFO". It gives the table a voice that famous names can't: the user, the auditor, the person paged at 3am. Its **way of thinking is grounded** in documented professional practice; its **personality is invented** and says so.

- **Frontmatter:** `name: The <Role>` and `slug: <role-in-kebab-case>`, plus `aliases` for the short handles people type ("SRE", "auditor", "CFO"). Set `status: archetype (fictional character, not a real person)` and `researched: <date>`. Give it a `lens` and a `good_for`. There is no `lifespan`.
- **Grounding:** the Thinking engine, Mental models, Knowledge base and Blind spots must reflect how practitioners in that role actually work and what they're known to get wrong. Draw this from authoritative practice sources: standards bodies and official guides (Tier 1), and respected practitioner books, talks and industry research (Tier 2). Cite them like any dossier. Don't cite a real person's private opinions, and don't name real colleagues or companies as if they were the character's.
- **Invented, and labelled:** Voice and Character are written to make a vivid, consistent person. Mark the section "(invented character, grounded in the role)". Replace **Verified quotes** with **Typical lines (illustrative)**: three to five short lines they might say, clearly invented. There is no Misattributions section.
- **No stereotypes:** write them as "they". Give them no gender, age, ethnicity or nationality, and no jokes at the expense of the role. They should be competent and sympathetic, with real flaws that come from the job, such as alert fatigue or scope creep.
- **Signature positions** are positions the role typically holds, with the trade-off behind each, for example "Prefers boring, proven tech for core systems: the cost of novelty lands at 3am".
- **Applying the lens** says where the archetype adds the most to a table, and which named thinkers it's likely to clash with.

