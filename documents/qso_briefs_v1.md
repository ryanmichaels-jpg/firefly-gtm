# Five QSOs — Firefly GTM Engine, Step 4 Deliverable

Generated **2026-06-22** from `data/mart/tam_scored.csv` (FORGE-A tier).
Source data: free public records only (CMS HGI, AHRQ Compendium, CMS POS, NPPES, Census Geocoder, mandates.csv, plus 14 named source URLs documented per QSO).
**Cost to produce: $0.**

## The 5

| # | Facility | State | Beds | System | Mandate | Play |
|---|---|---|---|---|---|---|
| 1 | [Harborview Medical Center](qso-briefs/qso-1-harborview.md) | WA | 413 | UW Medicine | RCW 49.19 — **In force** | Feb 14, 2026 ED rampage ($100K damage) → enforcement clock |
| 2 | [Clara Maass Medical Center](qso-briefs/qso-2-clara-maass.md) | NJ | 472 | RWJBarnabas Health | N.J.S.A. 26:2H-5.17 — **In force** | RWJB's 5-step framework + 1199SEIU contract pressure |
| 3 | [NewYork-Presbyterian Hospital](qso-briefs/qso-3-nyp.md) | NY | 2,262 | NYP Healthcare | Ch.618/2025 — **Upcoming 2027-01-01** | TVTP-grant playbook → 10+ campus scale-out before mandate |
| 4 | [CHRISTUS Spohn — Corpus Christi Shoreline](qso-briefs/qso-4-christus-spohn.md) | TX | 1,040 | CHRISTUS Health | SB240 — **In force** | Nov 13, 2024 dementia hoax — 50 officers, false alarm cost |
| 5 | [Our Lady of the Lake Regional Medical Center](qso-briefs/qso-5-our-lady-of-the-lake.md) | LA | 976 | FMOL Health System | Lynne Truxillo Act — **In force** | Two homicides (Truxillo 2019, Jackson 2025) + named-incumbent lawsuit |

## Methodology, briefly

**Selection criteria** (applied to 622 FORGE-A facilities to narrow to 5):

1. **forge_total = 27** (max — Fit × Acute=3 × Event=3 × Gravity=3)
2. **Exec-title EDM** (NPPES auth_official is C-suite)
3. **State diversity** — no two from the same state
4. **System diversity** — no two from the same parent system
5. **Mandate-status diversity** — at least 1 Upcoming (beat-the-clock) + at least 3 In-force (enforcement-risk)
6. **Geographic diversity** — West, East, South, Gulf
7. **Story diversity** — incident-driven, peer-leader, mandate-eponym, false-alarm, structural-litigation

**Signal density varies deliberately**:
- QSO 5 (Our Lady of the Lake) has the highest narrative density — two named homicides, active lawsuit, named incumbent vendor
- QSO 3 (NYP) is a *peer-leader* — they already lead on WPV; the play is scale-out before NY's 2027 deadline
- QSO 2 (Clara Maass) has medium signal — labor disputes + system-published WPV framework, not a specific incident
- This is the point: showing **how to write a one-off when the signal stack is dense vs sparse** is the actual GTM craft.

**Free sources only** (no Apollo, no Apify, no LinkedIn scraping):
- News & incident: GDELT / Google News / regional news outlets (KIRO 7, The Advocate, WAFB, KRIS TV)
- Existing WPV programs: AHA case studies, DHS TVTP grantee stories, hospital newsrooms
- Incumbent vendors: lawsuit filings (publicly named), competitor case-study pages where parseable
- Mandate text: published statutes via the project's `data/reference/mandates.csv`
- Buyer titles: NPPES authorized_official (for EDM), LinkedIn profile titles (public, view-only, not scraped)

## What each brief contains

Each `qso-briefs/qso-N-*.md` includes:

1. **Account at a glance** — CCN, beds, ED/BH, parent system, ownership, AHRQ flags
2. **FORGE rationale** — Acute / Event / Gravity scoring with the specific signal behind each
3. **The signal that makes this a QSO** — narrative section with dates, names, dollar amounts, evidence URLs
4. **Buying committee** — EDM (NPPES seed) + likely champion + sponsor + influencers, with sources
5. **One-off draft** — full email body, 80–125 words, ready to personalize
6. **Why this opening** — rationale for the specific framing
7. **Open follow-ups (Tier-C)** — what paid enrichment would add

## Non-negotiable constraint (per CLAUDE.md)

> **NEVER build email sequences. One-offs only.** Five emails written; each goes to one human about one event at one hospital. No drip cadence, no automation, no `{{first_name}}`.

## Important constraint on QSO 5

**Our Lady of the Lake has active wrongful-death litigation involving its security contractor (Inner Parish Security Corp).** Before sending the QSO-5 email externally, route through Firefly's CRO and Legal — vendor outreach that references the Jackson case may be inappropriate or may need outside-counsel pre-clearance. The brief is internal-use until that approval lands. See QSO-5 brief for full constraint section.

## What this is *not*

- Not a sequence. Not a template. Not synthetic.
- Not paid-enriched — Apollo / Apify / LinkedIn Sales Nav budgets reserved for QSO **scale-out** after these 5 have validated the model.
- Not a slide deck. The portfolio piece is exactly what's in this directory: data → score → 5 named hospitals → 5 named one-offs.

---

*Pipeline source map: [diagrams/source-map.svg](../diagrams/source-map.svg)*
*Underlying data: [data/mart/tam_scored_sample.csv](../data/mart/tam_scored_sample.csv) (PII redacted)*
*Mandate reference: [data/reference/mandates.csv](../data/reference/mandates.csv)*
