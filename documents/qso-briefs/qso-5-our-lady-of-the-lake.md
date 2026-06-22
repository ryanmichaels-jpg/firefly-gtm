# QSO 5 — Our Lady of the Lake Regional Medical Center (Baton Rouge, LA)

**Status**: `is_qso_candidate=TRUE` · forge_total **27** · facility_tier **1** · forge_tier **A** · **highest narrative density**

## Account at a glance

| | |
|---|---|
| CCN | 190064 |
| Beds | 976 |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — Level II Trauma + flagship academic |
| Parent system | Franciscan Missionaries of Our Lady Health System (5+ facilities, Catholic) |
| Ownership | Voluntary non-profit, church |
| Safety-net flags (AHRQ) | high DSH ✓ |

## FORGE rationale

- **Acute = 3** — high-DSH + behavioral health + **two documented WPV homicides** at this facility (Truxillo 2019, Jackson 2025)
- **Event = 3** — **R.S. 40:2199.11–.19 (Lynne Truxillo Act)**, **In force** — the law is **named after their employee**
- **Gravity = 3** — exec-title NPPES auth_official (CEO) + 976 beds + 5-facility FMOL system

## The signal that makes this a QSO

This is the most signal-dense QSO in the set. Two documented homicides:

**2019 — Lynne Truxillo (RN, BH unit)**: Patient Anthony Guillory attacked another nurse in OLOL's behavioral health unit at the Mid City campus on April 4, 2019. Truxillo, 56, intervened to pull Guillory off her colleague. Guillory then turned on her, grabbed her by the back of the neck, and struck her head against a desk. She died days later from blood clots ruled by the East Baton Rouge Parish Coroner as directly connected to the assault ([The Advocate](https://www.theadvocate.com/baton_rouge/news/crime_police/article_53f6af60-770c-11e9-b2c6-0ba9db15acf7.html) · [WAFB](https://www.wafb.com/2019/05/06/death-nurse-hands-patient-renewing-focus-workplace-violence/)). The **Lynne Truxillo Act** (R.S. 40:2199.11–.19) was passed in her memory.

**March 19, 2025 — Patricia ("Pattie") Jackson (OLOL employee)**: Shot multiple times by her estranged partner Roland Domino in OLOL's employee parking lot. Domino had been **loitering near her car for hours** before she arrived. He pleaded guilty to second-degree murder in May 2026 ([The Advocate lawsuit coverage](https://www.theadvocate.com/baton_rouge/news/courts/our-lady-of-the-lake-lawsuit-patricia-jackson-killing/article_8451c813-e09d-4dd8-be08-dfdea6e42cab.html) · [WBRZ](https://www.wbrz.com/news/family-suing-hospital-and-security-after-relative-was-murdered-as-she-left-work/) · [WAFB plea coverage](https://www.wafb.com/2026/05/11/man-pleads-guilty-second-degree-murder-hospital-parking-lot-shooting/)).

**Active lawsuit (2025–)**: Jackson's children filed wrongful death against OLOL **and its security contractor, Inner Parish Security Corp**, alleging the contractor "negligently failed in its duties to protect hospital staff by allowing Domino to loiter on hospital premises for hours." The lawsuit is the operational pressure; the incumbent vendor is named.

**Identified incumbent**: Inner Parish Security Corp (named in lawsuit — likely contract guard services, not necessarily the panic/duress/detection layer, but the perimeter-monitoring failure is at the heart of the case).

The Truxillo Act is in force statewide; OLOL is the eponym facility. After Jackson, the moral and legal pressure is at maximum.

## Buying committee

| Role | Name | Source | Notes |
|---|---|---|---|
| EDM (NPPES seed) | **Chuck Spicer** | NPPES auth_official | CEO, OLOL Regional Medical Center |
| Likely current CNO/champion | **Heather Runnels DNP, RN, NEA-BC** | [LinkedIn](https://www.linkedin.com/in/heather-runnels-dnp-rn-nea-bc-332a30198/) | OLOL nursing executive — directly downstream of the Jackson case |
| System sponsor | **Richard Vath** (FMOLHS system CEO) — confirm via fmolhs.org | system-wide post-Jackson decision-maker |  |
| Likely champion | **Director of Security & Safety, OLOL** | confirm via IAHSS LA chapter | role under acute scrutiny post-Jackson lawsuit |
| Influencer | **Lynne Truxillo's surviving family / Truxillo Foundation if exists** | mandate eponym connection |  |
| Incumbent | **Inner Parish Security Corp** | named in Jackson lawsuit | RFP-defense status: contract may be revisited post-litigation |

## One-off draft

**To:** Chuck Spicer, CEO, Our Lady of the Lake Regional Medical Center
**CC:** Heather Runnels (Nursing Executive); Director of Security & Safety, OLOL
**Subject:** The Truxillo Act + Pattie Jackson + Inner Parish — what's next?

Chuck —

The Lynne Truxillo Act is the only state WPV statute I know of named after the eponym hospital's own employee. After Pattie Jackson in March, the legal and moral pressure inside FMOL has to be off the chart — and the Inner Parish lawsuit means perimeter monitoring is suddenly on every board packet.

Firefly Lattice was built for exactly this gap. AI-confirmed loiter detection on the parking-lot perimeter, gunshot acoustics inside, panic-button mesh on a private RF gateway that doesn't depend on your contracted guards being awake. Detect → Locate → Alert → Respond. The detection layer your incumbent contract doesn't cover.

15 minutes? I'm conscious of the active litigation; I'm not here to leverage it — just to make sure the technology gap is one OLOL can close.

— Ryan, Firefly

## Why this opening

- **Names both victims** — Truxillo (2019) and Jackson (2025). This is the hospital where the law is named after their own dead employee. Anything less specific is disrespectful.
- **Names Inner Parish Security by name** — that's the incumbent the lawsuit is naming. Mentioning it shows real research; mentioning it carefully (no leverage statement) shows judgment.
- **"loiter detection on the parking-lot perimeter"** — Pattie Jackson's killer loitered for hours. The product fit is exact, not analogous.
- **"detection layer your incumbent contract doesn't cover"** — frames Firefly as complementary, not replacement. Contract guards still have a role; Lattice fills the sensing layer.
- **Closing reassurance — "I'm not here to leverage it"** — a normal sales pitch would walk into the litigation as ammo. The right move at OLOL is the opposite. That stance is what gets the 15-minute meeting.
- **125 words. Two CCs. No exclamation marks.**

## Important constraints (per CLAUDE.md guardrails)

- This brief is for **internal Firefly use only**. Do not send the email until OLOL Legal posture is checked — the active wrongful-death litigation may make outbound contact about the Jackson incident inappropriate. The CEO's outside counsel may want to pre-clear any vendor outreach that touches the lawsuit.
- **Pattie Jackson and Lynne Truxillo are named in their honor**, not as marketing material. Any mention in the actual sent email must read with that tone or it should not be sent.
- Recommended escalation: route this brief to Firefly's CRO + Legal before any send.

## Open follow-ups (Tier-C)

- Confirm Inner Parish Security Corp's contract scope (is it just guards, or guards + sensor layer?)
- Pull FMOLHS IRS Form 990 — Schedule H — for WPV program narrative + budget line
- Identify named Director of Security at OLOL via IAHSS LA chapter
- Check whether OLOL post-Jackson has issued an RFP for security technology
- Note: AHA published a December 2024 case study on OLOL Health Louisiana ([aha.org link](https://www.aha.org/case-studies/2024-12-23-our-lady-lake-health-louisiana)) — pull for context on whatever program they were running pre-Jackson
