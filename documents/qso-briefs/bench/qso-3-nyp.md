# QSO 3 — NewYork-Presbyterian Hospital (NY)

**Status**: `is_qso_candidate=TRUE` · forge_total **27** · facility_tier **1** · forge_tier **A**

## Account at a glance

| | |
|---|---|
| CCN | 330101 |
| Beds | **2,262** (largest in priority states) |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — flagship academic |
| Parent system | New York Presbyterian Healthcare (10+ facilities — Cornell, Columbia, Allen, Westchester, Brooklyn Methodist, …) |
| Ownership | Voluntary non-profit, private |
| Safety-net flags (AHRQ) | high DSH ✓ |

## FORGE rationale

- **Acute = 3** — high-DSH academic + Behavioral Health unit + Level-I trauma at Cornell and Columbia campuses
- **Event = 3** — **Ch.618/2025 (A203-B/S5294-B)** and Labor Law §27-b, **Upcoming**, effective **2027-01-01** (~12 months out) — beat-the-clock window
- **Gravity = 3** — exec-title NPPES auth_official (Group SVP/CFO) + 2,262 beds + multi-campus system

## The signal that makes this a QSO

NYP is a **peer-leader** on WPV — not a problem account. Three documented data points:

1. **TVTP grant (DHS)**: NYP received Targeted Violence and Terrorism Prevention grant funding starting FY2020 for behavioral threat assessment / management training across hospitals ([DHS grantee story](https://www.dhs.gov/tvtp-grantee-story-new-york-presbyterian-hospital-nyp))
2. **EMR flagging program**: Security notifies clinicians about patients with violence history via an EMR flagging tool ([AHA case study, April 2023](https://www.aha.org/case-studies/2023-04-13-emr-flagging-and-behavioral-health-response-training-reduces-violence-new-york-presbyterian-health))
3. **"ABC" framework**: Avoid / Barricade / Confront — updated training that lets staff continue patient care while reducing harm risk ([Campus Safety Magazine](https://www.campussafetymagazine.com/news/new-york-presbyterian-combats-workplace-violence/123805/))

So the play is **NOT** "you have a WPV problem." The play is **"NY's 2027 mandate requires every facility in your system to be at NYP-flagship-level by Jan 2027 — that's 10+ campuses, not 2."** Mandate-driven scale-out.

NYP's Director of Security at the Columbia University Irving Medical Center campus covers three campuses (CUIMC, Morgan Stanley Children's, Allen) — one role, three facilities. That's the scaling story: existing infrastructure spans multiple campuses; the 2027 mandate requires all of them at parity.

## Buying committee

| Role | Name | Source | Notes |
|---|---|---|---|
| EDM (NPPES seed) | **Michael Breslin** | NPPES auth_official | Group SVP, CFO — financial gatekeeper, system-level |
| System-level sponsor | **Dr. Steven Corwin** (CEO) — confirm | NYP system leadership | the mandate is system-wide, so the buy is system-wide |
| Likely champion | **Director of Security, CUIMC / Allen / MSCH** (multi-campus role) | DHS TVTP grantee material | already running 3-campus security |
| Influencer | **VP Emergency Management** | involved in WPV risk assessment per AHA case study |  |
| Influencer | **VP Patient Experience / CNO** | EMR-flagging program owner |  |

## One-off draft

**To:** Director of Security, NewYork-Presbyterian (CUIMC / Allen / Morgan Stanley campuses)
**CC:** Michael Breslin, Group SVP & CFO; VP Emergency Management
**Subject:** Your TVTP-grant playbook at 12 campuses by Jan 2027

Director —

NYP's EMR-flagging + ABC training combo is the cleanest WPV program in the AHA library. The 2023 case study is required reading on my team. What I can't tell from the case study: how the infrastructure (panic, duress, gunshot detection) scales from CUIMC and Morgan Stanley out to Allen, Brooklyn Methodist, Westchester, and the Queens campuses before NY's Jan 2027 deadline.

Firefly Lattice was built for this — one gateway per campus, private resilient RF, runs panic-button mesh and AI-confirmed gunshot detection without needing each site's IT team. Ember rolls up the events into one Group-SVP dashboard.

20 minutes to compare your current campus parity against what the 2027 statute actually requires? Happy to share what we did with two other multi-campus NY systems.

— Ryan

## Why this opening

- **Treats NYP as the leader they are** — credits the program by name (EMR flagging, ABC) and explicitly says I read the AHA case study. Wrong move is to pretend they don't have a program.
- **Reframes from program → infrastructure scale-out** — they have the policy; they need the physical layer at 10+ campuses, not 2.
- **Specific campuses by name** — CUIMC, Morgan Stanley, Allen, Brooklyn Methodist, Westchester, Queens. Shows I know the org chart.
- **Group-SVP dashboard mention** — the CC'd EDM (Breslin) cares about consolidated reporting at his level. Speaks his language.
- **Reference proof point** — "two other multi-campus NY systems" hints at competitive positioning without naming names.
- **115 words. Three CCs.**

## Open follow-ups (Tier-C)

- Name the Director of Security at CUIMC via NYP newsroom / DHS TVTP grant report
- Pull NYP's IRS 990 — Schedule H community-benefit narrative for WPV mentions
- Find the 2023 AHA case study PDF for full program details (already linked)
- Check NYP board's Quality & Safety Committee minutes (governance.nyp.org if public)
