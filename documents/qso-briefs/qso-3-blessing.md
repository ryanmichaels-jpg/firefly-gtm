# QSO 3 — Blessing Hospital (Quincy, IL)

**Status**: `is_qso_candidate=TRUE` · forge_tier **B** · StandaloneScore **82** · regional independent

## Account at a glance

| | |
|---|---|
| CCN | 140015 |
| Beds | 312 |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — regional referral hospital, western IL / eastern MO / NE MO corridor |
| Parent system | **Blessing Health System** (2-hospital: Blessing Quincy + Illini Community Pittsfield · std=82) |
| Location | 1005 Broadway, Quincy, IL 62301 |
| Ownership | Voluntary non-profit — Private |
| Service area | "Tri-State" — western IL, northeast MO, southeast IA |

## FORGE rationale (additive · max 9)

- **Acute = 3** — OSHA SIR-documented patient-on-staff assault, citation-grade
- **Event = 3** — IL Health Care Violence Prevention Act (210 ILCS 160) **in force since 2019**, **HB3435 amendment** signed into law as PA 104-0306 on **August 15, 2025** — adds reporting + recordkeeping + alarm/security assessment requirements
- **Gravity = 2** — independent CEO + exec NPPES seed (VP Finance), but 2-facility system (not pure standalone)
- **forge_total = 8 / 9**

## Why this is a QSO — the HARD GATE

**OSHA SIR #1855612** — **September 28, 2024** ([osha.gov/severe-injury-reports](https://www.osha.gov/severe-injury-reports)) — verbatim narrative:

> *"On September 28, 2024, an employee was walking down the hall when a patient ran toward him and knocked him to the floor, causing him to strike his head on the ground. The employee sustained a head injury…"*

Patient charged at staff, ambush-style, in a hallway. Intracranial injury logged. Employer self-report — no transported-to ambiguity.

## Why this fits the thesis

- **Regional referral standalone** — Blessing's 2-facility footprint (Quincy + the much-smaller Pittsfield critical-access) makes it functionally a single-campus operation; std=82.
- **Western IL geography** — distinct from the urban-NY anchors; portfolio diversification.
- **IL law just got teeth** — HB3435 (PA 104-0306) August 2025 added explicit **alarm/security assessment requirements** plus reporting + recordkeeping. The Sept 28 incident sits inside the amendment's lookback window.
- **Tri-State EMS hub** — regional referral status means trauma volume from three states routes through this ED; security demands scale with that volume.

## Buying committee

| Role | Likely Name | Source | Notes |
|---|---|---|---|
| **CEO / EDM sponsor** | **Brian Canfield, MHA, MBA, MA, FACHE** | [Blessing Health — Canfield announcement](https://www.blessinghealth.org/news/canfield-assume-leadership-blessing-health) · [WGEM](https://www.wgem.com/2023/02/16/blessing-health-system-names-next-president-chief-executive-officer/) | President/CEO of Blessing Health since July 2023 (succeeded Maureen Kahn) |
| **Champion (security) — CONFIRMED via Apify LinkedIn** | **David Schlosser, Security Officer** | [LinkedIn](https://www.linkedin.com/in/david-schlosser-0513437b) | Blessing Health security |
| Champion (info-sec / tech procurement) | **Andrew S., CISO, CISM** | [LinkedIn](https://www.linkedin.com/in/andrew-s-0723a537) | Enterprise & regulated environments |
| Likely sponsor | **Brian Canfield** + COO | mid-size system → CEO-direct security capex | |
| Influencer | **CNO** | Sept 2024 head-injury victim was floor staff | |
| Influencer | **VP Finance, CAO Blessing Corporate** | NPPES auth_official seed | functional, controls capex line items |
| Influencer (risk) — CONFIRMED | **Justin McDermott, MBA, CHES** — Risk Manager | [LinkedIn](https://www.linkedin.com/in/justin-mcdermott-mba-ches-85147063) | Blessing Health System Risk Manager — OSHA SIR reporter |
| Influencer (CFO) — CONFIRMED | **Pat Gerveler, CFO** | [LinkedIn](https://www.linkedin.com/in/pat-gerveler-71758892) | controls security capex |
| Influencer (Legal) — CONFIRMED | **Diane G., VP & Chief Legal Officer** | [LinkedIn](https://www.linkedin.com/in/dianegjacoby) | HB3435 compliance |
| Influencer (COO) — CONFIRMED | **Tim Tranor, COO** | [LinkedIn](https://www.linkedin.com/in/tim-tranor-35a25852) | day-to-day ops decision-maker |

## One-off draft

**To:** Brian Canfield, President & CEO, Blessing Health System
**CC:** Director of Public Safety, Blessing Hospital
**Subject:** Head injury Sept 28 from a patient charging in a hallway — and HB3435 just added the security-assessment requirement

Brian,

September 28, 2024: A patient charged your staff member in a hallway and knocked him to the floor — head injury, OSHA SIR ID 1855612, your team filed it.

August 15, 2025: Pritzker signed HB3435 (PA 104-0306). 210 ILCS 160 now requires alarm and security assessment as part of the WPV program, plus expanded reporting and recordkeeping. As a regional referral hub serving the Tri-State, your security plan is on the visible-compliance side of that.

The Sept 28 pattern — patient running at staff, ambush style, hallway — is one of the clearest detect-locate-alert cases Firefly Lattice + Ember handle. AI loiter and approach detection picks up the patient's run trajectory before contact; the nearest responder gets the unit + bed; staff has a wearable panic device on a private RF mesh that works during a Wi-Fi outage.

15-minute call? I'll show you how it would route on a hallway pattern, what it costs to operate vs the alarm-assessment line item HB3435 added, and how a 2-hospital independent deploys without a vendor-IT integration ladder.

— [Rep]

---

## Evidence URLs

- OSHA SIR (Sept 28 2024 hallway head-injury attack): [osha.gov/severe-injury-reports](https://www.osha.gov/severe-injury-reports)
- Mandate: [Illinois HB3435 — ILGA](https://ilga.gov/Legislation/BillStatus?DocNum=3435&GAID=18&DocTypeID=HB&LegId=162063&SessionID=114) · [210 ILCS 160 Health Care Violence Prevention Act](https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3906&ChapterID=21)
- CEO: [Brian Canfield assumes leadership — Blessing Health](https://www.blessinghealth.org/news/canfield-assume-leadership-blessing-health)
