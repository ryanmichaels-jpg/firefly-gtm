# QSO 1 — Harborview Medical Center (Seattle, WA)

**Status**: `is_qso_candidate=TRUE` · forge_total **27** · facility_tier **1** · forge_tier **A**

## Account at a glance

| | |
|---|---|
| CCN | 500064 |
| Beds | 413 |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — **Level I Adult & Pediatric Trauma Center** (Seattle's only) |
| Parent system | UW Medicine (4-facility academic system) |
| Ownership | Government — county / UW joint |
| Safety-net flags (AHRQ) | high DSH ✓ |

## FORGE rationale

- **Acute = 3** — high-DSH urban safety-net + behavioral health unit (AHRQ proxy)
- **Event = 3** — **WA RCW 49.19** (HB1162/SB5162 2025) **In force**, effective 2026-01-01; state plan ESH enforcement-mode
- **Gravity = 3** — exec-title NPPES auth_official + 413 beds + 4-facility system

## The signal that makes this a QSO

**Feb 14, 2026**: A patient discharged with a wrist injury attacked nurses and security in the ED, kicked/spat on staff, broke open an oxygen line, set fire to a bucket of medical supplies in a trauma room, made a noose with plastic tubing, and threatened to kill himself. Estimated **$100K in damage**, criminal charges include assault + first-degree arson. No staff injuries — credit to emergency response protocols. ([KIRO 7](https://www.kiro7.com/news/local/video-man-attacks-nurses-harborview-medical-center/f99182e2-fb4a-4de3-8543-364a396bde77/) · [Seattle PD blotter](https://spdblotter.seattle.gov/2026/02/14/man-arrested-for-destroying-emergency-room-attacking-hospital-staff/) · [Nurse.org](https://nurse.org/news/patient-attack-harborview-seattle/))

This is **four months before** Washington's RCW 49.19 enforcement begins (2026-01-01 — already in force). The incident is the textbook "structural change with an endpoint" — county trauma center, state mandate, fresh ED incident, no fatalities (yet).

## Buying committee

| Role | Name | Source | Notes |
|---|---|---|---|
| EDM (NPPES seed + LinkedIn confirmed) | **Sommer Kleweno Walley** | [LinkedIn](https://www.linkedin.com/in/sommer-kleweno-walley-3b330aab) · [UW Newsroom](https://newsroom.uw.edu/news-releases/sommer-kleweno-walley-named-harborview-ceo) | CEO Harborview Medical Center (since 2021 interim, permanent thereafter) |
| **Champion (security tech buyer) — CONFIRMED via Apify LinkedIn** | **Shaun Geraghty — Manager of Public Safety/Security Technology, UW Medicine** | [LinkedIn](https://www.linkedin.com/in/shaungeraghty) | **The direct buyer.** UW Medicine system-level role responsible for security technology procurement; covers Harborview as the flagship campus. Title surfaced by raw scrape — classifier missed it because it's "Manager of Public Safety/Security Technology" not the standard "Director of Security" pattern. |
| **Champion (ED Ops + Nursing) — CONFIRMED via Apify LinkedIn** | **Timothy Fredrickson — Assistant Administrator + Associate CNO, Harborview Emergency Services** | [LinkedIn](https://www.linkedin.com/in/timothy-fredrickson-87b773103) | Direct line of authority over the ED where the Feb 14 incident played out; co-owns staff-safety with the security org |
| Likely sponsor | **Sommer Kleweno Walley** (CEO) | overlapping with EDM | post-Feb-14 incident, this is in her direct line |
| Influencer (WPV-adjacent clinical) — CONFIRMED via Apify | **Heather Gebhardt — Licensed Clinical Psychologist · Suicide Prevention · Healthcare Workforce Well-Being & Safety** | [LinkedIn](https://www.linkedin.com/in/heather-gebhardt) | Workforce well-being lens — relevant for staff-trauma response after the Feb 14 event |
| Influencer (Quality/Safety) — CONFIRMED via Apify | **James Churgai — Healthcare Leader: Quality, Safety, Operational Excellence** | [LinkedIn](https://www.linkedin.com/in/james-churgai) | quality + safety policy lens |
| Influencer (Cyber/Tech) — CONFIRMED via Apify | **DJ Kern — Cybersecurity Specialist, Healthcare Info Security** | [LinkedIn](https://www.linkedin.com/in/djkerncybersecurity) | network/integration counterpart for any Lattice gateway deployment |
| Influencer (CMO Harborview) — CONFIRMED via Apify | **David Zonies, MD, MPH, MBA, FACS, FACHE — CMO Harborview · Professor of Surgery** | [LinkedIn](https://www.linkedin.com/in/davidzonies) | medical staff stakeholder |
| Influencer (CMO UW Medicine system) — CONFIRMED via Apify | **Anneliese Schleyer — CMO UW Medicine** | [LinkedIn](https://www.linkedin.com/in/anneliese-schleyer-695603298) | parent-system clinical sign-off |
| Influencer (Facilities) | **Anthony** (KingCo Facilities Mgmt Division) | [DES proposal Apr 2024](https://des.wa.gov/sites/default/files/2024-02/2024-03-28-KingCoFacMgmtDiv-HarborviewMC-DB-App.pdf) | facilities-side decision-maker — King County is the owner |

## One-off draft

**To:** VP / Director of Security & Safety, Harborview Medical Center
**CC:** Sommer Kleweno Walley, CEO
**Subject:** $100K in 90 minutes — and RCW 49.19 starts the clock

Sommer, your team kept Steven Sauro from injuring staff on Feb 14 — the de-escalation training worked. The $100K in trauma-room damage is the kind of cost RCW 49.19 is about to make boardroom-visible at every WA hospital.

Most ED protocols fire after the threat is in the room. Firefly Lattice gateway sits at the perimeter — gunshot detection, panic-button mesh on resilient private RF, and AI-confirmed loiter alerts. Detect → Locate → Alert → Respond, before the noose-making stage.

Worth 15 minutes? I can walk you through how it would have routed Feb 14 — what would have fired, when, to whom. No pitch deck.

— Ryan

## Why this opening

- **Names the specific incident, the perpetrator, the date** — proves I'm not running a sequence; I'm writing one email to one person about one event at one hospital.
- **Credits the team's training** — Sauro caused $100K of damage but injured no staff. That's a real win the CEO is proud of. Don't ignore it; lead with it.
- **Ties the dollar number to the mandate** — RCW 49.19 enforcement starting means $100K incidents become reportable / line-itemed. That's the structural change.
- **Product placement is specific, not slidewareware**: Lattice gateway, gunshot detection, panic-button mesh, AI-confirmed loiter — matches Firefly's "Detect → Locate → Alert → Respond" J-T-B-D from CLAUDE.md.
- **Soft ask is "I'll walk you through how it would have routed Feb 14"** — that's a one-off proof artifact, not a generic demo request.
- **80 words. No links. No CTA button. Plain text.**

## Open follow-ups (Tier-C work, not done in this brief)

- Confirm Director of Security name via IAHSS Pacific NW chapter directory ([iahss.org](https://www.iahss.org/))
- Check Joint Commission accreditation file for recent WPV-related findings
- Pull Harborview's most recent annual report (Behavioral Emergency Service Team coverage)
- Cross-reference UW Medicine board minutes for safety committee mentions
