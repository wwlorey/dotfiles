---
name: storybrand-website
description: Translating a completed StoryBrand SB7 BrandScript into a high-converting website using the Hero / 3Ps / FOMO three-section layout. Consult whenever the user asks to build, plan, redesign, or write copy for a website based on StoryBrand, SB7, or a BrandScript — or asks for website hero copy, landing-page structure, or a BrandScript-to-website mapping. If the user wants to write the BrandScript first, hand off to the `storybrand` skill.
---

# StoryBrand Website

Turn a completed SB7 BrandScript into a website specified by the **three-section layout**: Hero → 3Ps (Promise, Proof, Plan) → FOMO. Stop thinking in seven elements; think in three sections, each pulling specific parts of the BrandScript.

If the BrandScript is missing or incomplete, stop and route the user to the `storybrand` skill first. Do not invent BrandScript values to keep momentum — the website is downstream.

The deep theory of each section, the design principles that apply everywhere (Morse code writing, clarity over cleverness, one CTA, Rule of Three, speed, loss aversion, etc.), the multiple-revenue-streams pattern, and the full implementation checklist live in `references/website-spec.md`. Open it on demand when:

- You need worked examples or copy patterns for a section (yes-questions, fear appeal, testimonial story arc).
- The user has multiple products/divisions and you need the umbrella-message pattern.
- You're about to finalize copy and want the implementation checklist as a verification pass.
- The user pushes back on a rule and you need the rationale.

## Workflow

1. **Confirm the BrandScript is complete.** All 7 elements filled in: Character, Problem (villain + external + internal + philosophical), Guide (empathy + authority), Plan, CTAs (direct + transitional), Failure, Success — plus a one-liner. If anything is missing, route back to `storybrand`.
2. **Draft Section 1 — Hero** (see below).
3. **Run the grunt test** on the hero. Can a stranger answer offer / benefit / next-step in 5 seconds? If not, rewrite before continuing.
4. **Draft Section 2 — 3Ps** (Promise, Proof, Plan).
5. **Draft Section 3 — FOMO** (Failure + Transitional CTA).
6. **Apply the universal principles** (Morse code, one repeated CTA, Rule of Three, loss aversion). Open `references/website-spec.md` for the full list.
7. **Verify against the implementation checklist** in the reference before declaring done.

## Section 1: Hero (above the fold)

The most important section. Decisions made in seconds.

**BrandScript source:** Problem (philosophical) → headline; Character + Plan + Success → clarifying sentence; CTAs → buttons.

What goes here:
1. **Philosophical statement as the headline** — the hook that invites people into the story. Examples: *"Filing taxes doesn't need to be difficult."* / *"Buying a home should be exciting, not stressful."* / *"Just do it."* If the BrandScript lacks a strong philosophical angle, use an aspirational identity statement or direct promise of the desired outcome instead.
2. **One clarifying sentence underneath** — plain noun-level description of what you do. The one-liner (*"We help [character] who struggle with [problem] by [plan] so they [success]"*) often works perfectly here or as the meta description.
3. **Direct CTA button** — brightest, most obvious element on the screen.
4. **Optional transitional CTA** — secondary, less prominent.

Design rules for the hero:
- **Don't fill the entire viewport.** Hint at the next section so users want to scroll.
- **Images of success** — happy people using/experiencing the outcome. Not your building, not your team photo.
- **Nav:** CTA in the top-right corner, contrasting color. Keep the menu clean — footer is the junk drawer (About, Team, Careers, Privacy).

**Grunt test, here, every time.** A stranger should answer in 5 seconds: *What do you offer? How will it make my life better? What do I do to buy it?*

## Section 2: The 3Ps

The argument for why someone should work with you.

### 2A: Promise

**BrandScript source:** Character (want) + Problem (internal/philosophical) + Success.

Make the customer feel understood and paint the gap between where they are and where they want to be.

**Best technique:** 3–4 yes-questions where the ideal customer's answer is "yes" to all. Getting agreement makes them more agreeable to your CTA. Example (web design agency):
> *Do you struggle with writing website copy?*
> *Do you wish you could just press fast-forward?*
> *Is this project going to make you a lot of money if done right?*

Then bridge from pain to your solution:
> *[Brand] is a company that [does X] for [people who Y] without [the thing they hate].*

Rules:
- **Stay in emotional/philosophical territory.** Internal problems hit harder than external ones.
- **Use loss aversion framing.** "Don't keep wasting money on ads that don't work" beats "Save money on better ads." People fear missing out more than they crave gain.
- **Apply the contrast effect.** Life-with-you vs. life-without-you beats abstract promises.
- **Map success to a psychological need:** status, completeness, or self-realization. Be specific and visual (Kennedy: "put a man on the moon," not "competitive space program").

If yes-questions don't fit, write 1–2 paragraphs describing the problem landscape — keep it emotional, not technical.

### 2B: Proof

**BrandScript source:** Guide (empathy + authority).

Three components, in order:
1. **Introduce the empathetic guide.** Just enough origin story that the customer identifies you as someone who walked a similar path. Don't take up too much space — you're the guide, not the hero. A little mystery goes a long way.
2. **Stories of transformation (testimonials).** Use the arc *"I was experiencing [problem] and couldn't find anyone to help. Then I met [brand] and they [made it better in specific way]. I highly recommend them."* Video testimonials always outperform text. **3 is the sweet spot. More than 10 makes you look like the hero.**
3. **Logos, certifications, awards.** Social proof — client logos (especially recognizable ones), industry certs, awards. Place them here, not scattered.

### 2C: Plan

**BrandScript source:** Plan.

Removes fear and confusion from the buying process. Choose **one** plan type — **never mix**.

- **Pre-purchase plan** (how to get started): everything leading up to the sale. Make it easy to take the first step.
  > *1. Book a call. 2. Tell us your challenges. 3. Get a proposal within 24 hours.*
- **Post-purchase plan** (your secret framework): what happens after they buy. Positions you as the expert.
  > *1. Take our 6-part assessment. 2. Get a custom program. 3. Attend weekly check-ins.*

**When in doubt, use pre-purchase.** Easier to create, easier to understand. Post-purchase plans tempt jargon and step bloat.

Rules:
- **Exactly 3 steps.** The brain struggles to hold more than three. (Why phone numbers are 3-4-4.) If reality has 20 steps, group into 3 phases.
- **Name the plan.** A named plan has dramatically higher perceived value ("The Easy Installation Plan").
- **Never combine pre- and post-purchase** into one sequence.
- **Consider a guarantee near the plan** ("Satisfaction guaranteed," "Money back," "3-year warranty") to alleviate trust obstacles.

**Optional: Agreement Plan** alongside the process plan — a list of promises addressing specific customer fears (CarMax: *no haggling, no commission salespeople, every car certified*). Often lives on a "why us" section, not above the fold.

## Section 3: FOMO

**BrandScript source:** Failure + Transitional CTA.

### 3A: Failure (the stakes)

Short, pointed message about the cost of inaction. If there's no cost to not hiring you, there's no reason to hire you. This is the "pinch of salt" — twist the knife just enough.

**Fear Appeal (4 steps):**
1. **Establish vulnerability.** *"Nearly 30% of homes have termite damage."*
2. **Establish that action reduces it.** *"You should do something about it."*
3. **Offer a specific protective action.** *"We offer a complete home treatment."*
4. **Challenge them to take it.** *"Schedule today."*

Frame around what they **lose**, not gain:
- Lost money, lost time, ongoing frustration
- The problem getting worse
- Competitors pulling ahead

### 3B: Transitional CTA (lead magnet)

Not everyone is ready to buy. Offer something irresistible in exchange for a way to stay in touch (usually email).

Formats: free PDF / downloadable guide; free assessment or quiz; video series or webinar; free trial or demo; checklist or template.

The transitional CTA should:
1. **Stake a claim to your territory** (position as expert)
2. **Create reciprocity** (giving freely makes people want to give back)
3. **Keep the relationship alive** (you can follow up)

## Universal principles (apply everywhere)

Run these as a final pass. Full versions and rationale in `references/website-spec.md`.

- **Write in Morse code.** Cut text in half, then again. Best sites use <10 sentences total.
- **Clarity beats cleverness.** *"I'm a plumber. Affordable. We fix things fast."* > *"Turning your pipe dreams into reality."*
- **One CTA, repeated often.** Same wording, same color, in nav (top-right), hero, after 3Ps, after FOMO. People aren't annoyed — they're relieved to know what to do next.
- **Each page has one job.** Contact page drives contact, not blog reading.
- **Rule of Three.** 3 benefits, 3 services, 3 steps, 3 testimonials. Anything beyond three steals clarity.
- **Speed matters.** Fast load = professional. 1 sec delay = lost revenue.
- **Loss aversion over gain framing.** 2–3× motivational pull.
- **Before/after over abstract promises.** Show the transformation visually.
- **Consistency across channels.** Homepage headline echoes in social bio, email signature, elevator pitch.
- **Systems over rock stars.** Automated scheduling. Instant follow-up. Speed to lead.
- **Iterate, don't perfect.** Launch, measure, adjust.

## Multiple revenue streams

If the business has multiple products/divisions, don't list them equally above the fold. Find an **umbrella message** that unifies them, then split into sub-paths. Example: *"The key to success is a customized plan"* → buttons for "Personal" vs. "Corporate." Each sub-path can have its own sub-BrandScript and landing page; the homepage speaks to the shared core desire.

## Before declaring done

Verify against the full implementation checklist in `references/website-spec.md` (Hero, Promise, Proof, Plan, FOMO, Global). Don't ship until every applicable box is checked.

## BrandScript-to-website mapping (quick reference)

| BrandScript Element | Website Location | How It's Used |
|---|---|---|
| One-liner | Hero clarifying sentence + meta description | Verbal calling card across channels |
| Character (want) | Promise section | Yes-questions, pain description |
| Problem (philosophical) | Hero headline | Invites into the story |
| Problem (internal/external) | Promise section | Emotional pain points |
| Guide (empathy) | Proof section | Brief origin story |
| Guide (authority) | Proof section | Testimonials, logos, certs |
| Plan | Plan section | 3-step process (pre OR post purchase) |
| Direct CTA | Hero + nav + repeated | Primary button everywhere |
| Transitional CTA | FOMO + hero | Lead magnet, email capture |
| Failure | FOMO section | Cost of inaction (pinch of salt) |
| Success | Promise section + hero imagery | Aspirational outcome, success images |
