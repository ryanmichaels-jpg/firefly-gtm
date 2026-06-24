# QSO 2 — St Barnabas Hospital (Bronx, NY)

**Status**: `is_qso_candidate=TRUE` · forge_tier **A** · StandaloneScore **100** · safety-net standalone

## Account at a glance

| | |
|---|---|
| CCN | 330399 |
| Beds | 446 |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — Bronx safety-net, full psychiatric service |
| Parent system | **SBH Health System** (rebranded from "St Barnabas Hospital" in 2014; single-hospital system, std=100) |
| Location | 4422 Third Avenue, Bronx, NY 10457 |
| Ownership | Voluntary non-profit — Private |
| Affiliation | 160-year-old safety-net institution |

## FORGE rationale (additive · max 9)

- **Acute = 3** — OSHA SIR-documented patient-on-staff assault (psychiatric monitoring), citation-grade
- **Event = 3** — NY S5294-B effective **September 18, 2026** — Bronx population > 1M → ED guard / off-duty LEO REQUIREMENT applies (not just program plan)
- **Gravity = 3** — independent CEO + active $140M state-funded modernization announced by Gov. Hochul → safety capex window is open
- **forge_total = 9 / 9** (max)

## Why this is a QSO — the HARD GATE

**OSHA SIR #1972013** — **September 16, 2025** ([osha.gov/severe-injury-reports](https://www.osha.gov/severe-injury-reports)) — verbatim narrative:

> *"An employee was monitoring a psychiatric patient who was walking in the hallway. The patient grabbed the employee by the neck and threw her to the ground. She was hospitalized with an acute superior end-plate compression fracture…"*

This is the canonical Firefly use case: **a 1:1 psych observation goes physical**, employer self-reports to OSHA, patient is the attacker, employee is hospitalized with a spinal fracture. There is no transported-to ambiguity — OSHA SIR is by definition on-site (the employer reports their own facility's incident). The HARD GATE is met by employer's own legal disclosure.

Note: 160-year-old Bronx safety-net serving "predominantly low-income, high-need, multilingual, Latinx, and Black individuals and families who live within a mile of the hospital" — high-acuity behavioral health volume is structural, not anomalous.

## Why this fits the thesis

- **Single-hospital system** (SBH Health System operates only the Bronx campus + ambulatory clinics). std=100. Not a multi-hospital chain.
- **Bronx population >1 million** → S5294-B requires "at least one off-duty law enforcement officer or trained security personnel present at all times in the emergency departments" — the strictest provision in the law. This is mandate teeth specifically here.
- Geographically pairs with Richmond U (Staten Island) for shared NYC field motion.

## Buying committee

| Role | Likely Name | Source | Notes |
|---|---|---|---|
| **CEO / EDM sponsor** | **Dr. David Perlstein, MD, MBA, FAAP** | [AHA Chair File](https://www.aha.org/news/leadership-rounds/2024-02-26-chair-file-leadership-dialogue-driving-community-health-improvement-david-perlstein-md-sbh) · [LinkedIn](https://www.linkedin.com/in/david-perlstein-4882a218/) | President/CEO since July 2016; pediatrician; champions community health |
| **Champion (ED + Quality) — CONFIRMED** | **Edward Jarvis — Vice Chair, Dept of Emergency Medicine + Director of Quality, SBH Health System** | [LinkedIn](https://www.linkedin.com/in/edward-jarvis-930403110) | direct stakeholder in Sept 16 2025 psych monitoring incident; ED + Quality dual role makes him the WPV-program point person |
| **Champion (Facilities / physical-security capex) — CONFIRMED** | **Frank Conti — AVP Engineering & Facilities** | [LinkedIn](https://www.linkedin.com/in/frankconti) | $140M state-funded ED expansion runs through this seat |
| Champion (Nursing Quality) — CONFIRMED | **Dr. Tara M H., DNP — Executive Nursing Leadership, Quality Mgmt, Patient Safety** | [LinkedIn](https://www.linkedin.com/in/dr-tara-m-h-5478555) | Sept 2025 victim was a 1:1 psych observer (nursing staff) |
| Likely sponsor | **Dr. Perlstein** + COO | direct line at a 446-bed standalone | |
| Influencer (COO) — CONFIRMED | **Eric Appelbaum — COO + Senior EVP** | [LinkedIn](https://www.linkedin.com/in/eric-appelbaum-95bb6798) | day-to-day operations + capex sign-off |
| Influencer (CMO) — CONFIRMED | **Daniel Lombardi, DO, MBA, FACOEP — SVP/CMO** | [LinkedIn](https://www.linkedin.com/in/daniel-lombardi-do-mba-facoep-55021b31) | medical-staff stakeholder; FACOEP = emergency medicine certified |
| Influencer (IT/Info Sec) — CONFIRMED | **Renee Hulen, RN, MS — AVP IT / Clinical Informatics / InfoSecurity** | [LinkedIn](https://www.linkedin.com/in/renee-hulen-rn-ms-bha-iq-ci-499203a) | network/integration owner for any Lattice/Ember deployment |
| Influencer (Govt Affairs) — CONFIRMED | **Ninfa Segarra — SVP Government & Community Affairs** | [LinkedIn](https://www.linkedin.com/in/ninfa-segarra-3b136075) | manages the Hochul $140M relationship; safety-tech aligns with state's investment thesis |

## Capital context — the budget signal

**November 2024**: Governor Hochul announced **$140 million** for "transformational" upgrades to SBH Health System — ED capacity expansion, equipment upgrades, expanded community health partnerships. ([Bronx Times](https://www.bxtimes.com/gov-hochul-sbh-health-system/) · [Governor's office](https://www.governor.ny.gov/news/making-investments-bronx-governor-hochul-announces-support-new-safety-net-hospital-partnership)) Safety-tech RFPs typically follow major capital programs by 6–12 months. The September 2025 staff fracture happened **inside this capex window**.

## One-off draft

**To:** Dr. David Perlstein, President & CEO, SBH Health System
**CC:** Director of Security & Facilities VP (confirm)
**Subject:** Spine fracture in September, S5294-B in September, $140M capex now — what fires when on a 1:1 psych obs

Dr. Perlstein,

September 16: a 1:1 psych obs went physical — patient grabbed the staff member by the neck, threw her to the floor, acute superior end-plate compression fracture. OSHA SIR ID 1972013, your team filed it.

September 18, 2026: S5294-B becomes effective. Bronx is over 1M population — your ED needs at minimum one off-duty LEO or trained security at all times. That's not the same lift as a program plan; that's a staffing line.

The pattern that hospitalized your monitoring staff member is the pattern Firefly Lattice + Ember are purpose-built for. Wearable panic mesh on resilient private RF (works during a building network outage), AI loiter alerts that detect agitated escalation patterns before the patient grabs, automatic routing to the nearest security responder with the unit + bed identified — all integrated with the $140M ED expansion you're standing up.

15-minute call? I'll walk through how the alert would have routed at 09:16 on Sept 16 — and what the same alert would cost you to operate vs the all-hours LEO staffing the law now requires. No pitch deck.

— [Rep]

---

## Evidence URLs

- OSHA SIR (Sept 16 2025 psych monitoring fracture): [osha.gov/severe-injury-reports](https://www.osha.gov/severe-injury-reports)
- Mandate: [NY S5294-B](https://www.nysenate.gov/legislation/bills/2025/S5294/amendment/B) · [Haynes Boone analysis](https://www.haynesboone.com/news/alerts/mandatory-workplace-violence-prevention-requirements-for-new-york-healthcare-employers)
- CEO: [Dr. David Perlstein — AHA](https://www.aha.org/news/leadership-rounds/2024-02-26-chair-file-leadership-dialogue-driving-community-health-improvement-david-perlstein-md-sbh)
- Capex: [Hochul announces $140M for SBH — Bronx Times](https://www.bxtimes.com/gov-hochul-sbh-health-system/)
