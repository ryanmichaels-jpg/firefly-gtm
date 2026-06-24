# Firefly GTM Engine — session handoff (2026-06-24, PM)

> **Supersedes the 2026-06-23 PM handoff.** Read this + `CLAUDE.md` + `documents/qso_briefs.md` + everything in `context/` before running any skill.

---

## TL;DR

Portfolio v2 is **shipped and live**. Vercel production at https://dashboard-steel-omega-96.vercel.app is serving today's data (50-state universe, additive FORGE, 5 new QSOs). README, CLAUDE.md, RUNBOOK, docs/SOURCES, signal-library, and all per-QSO briefs reflect the current state. v1's 5 QSOs are archived to `documents/qso-briefs/bench/` (NYP, OLOL, Clara Maass, CHRISTUS) and their auto-generated artifacts moved to `documents/qso-briefs/auto/_archive/` with a README explaining why.

Repo: `~/Projects/firefly-gtm` · GitHub: https://github.com/ryanmichaels-jpg/firefly-gtm · Live: https://dashboard-steel-omega-96.vercel.app

---

## What v2 changed (since the 2026-06-23 handoff)

| Area | v1 (yesterday) | v2 (today) |
|---|---|---|
| Universe | 15 states, 2,353 facilities | **50 states + DC, ~5,362 facilities** |
| FORGE formula | Multiplicative (Fit × A × E × G, max 27) | **Additive: Fit × (A + E + G), max 9** + Standalone cap |
| Tier letters | A=broad, C=QSO | **A↔C flipped** — A=QSO, C=broad (matches grading intuition) |
| Acute Need source | AHRQ safety-net proxies | OSHA SIR (citation-grade) + HARD-GATE news classifier |
| 5 QSO selection | FORGE-27 + diversity | **HARD-GATE on-site violence + state mandate + std-first rank** |
| Buying committee | NPPES auth_official (proxy, no email) | **Apify LinkedIn role-mapped** + named champion per QSO |
| 5 QSOs | Harborview, Clara Maass, NYP, CHRISTUS Spohn, OLOL | **Richmond U, St Barnabas, Blessing, Mary Washington, Harborview** |

---

## The current 5 QSOs (LOCKED 2026-06-24)

Ranked by StandaloneScore desc. All pass HARD GATE + state mandate + footprint floor (beds ≥ 150).

| # | Facility | State | std | Beds | Mandate | Incident |
|---|---|---|---|---|---|---|
| 1 | [Richmond University Medical Center](documents/qso-briefs/qso-1-richmond-university.md) | NY | 100 | 473 | NY S5294-B · 2026-09-18 | Mar 2024 rampage + OSHA SIR Dec 2024 |
| 2 | [St Barnabas / SBH](documents/qso-briefs/qso-2-st-barnabas.md) | NY | 100 | 446 | NY S5294-B + Bronx LEO trigger | OSHA SIR Sep 2025 — psych nurse spinal fracture |
| 3 | [Blessing Hospital](documents/qso-briefs/qso-3-blessing.md) | IL | 82 | 312 | IL HB3435 (PA 104-0306) signed 2025-08-15 | OSHA SIR Sep 2024 — hallway charge head injury |
| 4 | [Mary Washington Hospital](documents/qso-briefs/qso-4-mary-washington.md) | VA | 71.5 | 451 | VA HB2269 · eff 2025-07-01 | Mar 2025 — deputy attacked at hospital |
| 5 | [Harborview Medical Center](documents/qso-briefs/qso-5-harborview.md) | WA | 64 | 413 | WA RCW 49.19 · eff 2026-01-01 | Feb 2026 ED rampage + arson ($100K) |

Each brief has: account snapshot · FORGE rationale · HARD-GATE incident · why-this-fits-thesis · 8–10 person buying committee with LinkedIn URLs · 80–150 word one-off draft.

---

## What's still local-only (gitignored)

Same posture as v1 — full data + secrets are local, only PII-redacted samples are pushed:

```
data/mart/tam.csv + tam_scored.csv     — full mart with edm_seed_name/phone (PII)
data/raw/                              — cached source pulls (large + regenerable)
.env                                   — API keys (Apify, Anthropic, others)
documents/qso-briefs/auto/linkedin-*.json — Apify scrape JSON for the 5 QSOs (PII)
skills/tier-b-news/ + skills/tier-b-techstack/ — uncommitted experimental skills
```

Pushed (PII-redacted): `tam_scored_sample.csv` (170 rows), `dashboard/data.json`.

---

## Apify state (as of this session)

| QSO | LinkedIn URL | Apify scan | Security champion |
|---|---|---|---|
| Richmond U | `linkedin.com/company/richmond-university-medical-center` | ✓ 100 employees | ✓ Michael Battiste (GC+SVP Legal & Risk) |
| St Barnabas | `linkedin.com/company/sbhbronx` | ✓ 100 employees | ✓ Edward Jarvis (Vice Chair Emergency Med + Director of Quality) |
| Blessing | `linkedin.com/company/blessing-health` | ✓ 100 employees | ✓ David Schlosser (Security Officer) + Andrew S. (CISO) |
| Mary Washington | `linkedin.com/company/mary-washington-healthcare` | ✓ 100 employees | ✓ Calvin Bostic, CPP, CHPA (Director Security/Safety/EM) |
| Harborview | `linkedin.com/company/harborview-medical-center` | ✓ 100 employees | ✓ Shaun Geraghty (Manager Public Safety/Security Tech, UW Medicine) |

All 5 LinkedIn scrapes complete. Title-pattern classifier in `skills/qso-linkedin/title-patterns.yaml` extended this session to catch "Manager of Public Safety/Security Technology" (UW Medicine pattern) and CISO/InfoSec patterns for influencers.

---

## Pipeline state (verified against `data.json` 2026-06-24)

- Total facilities in dashboard: **5,362**
- QSO count: **5**
- generated_at: **2026-06-24**
- Vercel production alias: **dashboard-steel-omega-96.vercel.app** → latest deployment (verified READY)

---

## The finish list (next session priorities)

**Status of the three v2 items (verified this session):**

1. **tier-b-contracts v2 — SAM.gov opportunities + recompete radar.** Execution plan written: `skills/tier-b-contracts/V2_PLAN.md`. SAM.gov key in `.env` verified valid; quota exhausted today (HTTP 429: "You can access API after 2026-Jun-25 00:00:00+0000 UTC"). Path A in the plan (USAspending recompete radar) is buildable without SAM.gov but requires re-pulling period_of_performance fields the v1 cache didn't capture (~30 min focused work). Path B (SAM.gov active opps) executes after midnight UTC tonight.
2. **tier-b-incumbent v2 — vendor case studies via Apify RAG Web Browser.** Execution plan written: `skills/tier-b-incumbent/V2_PLAN.md`. 8 vendor case-study URLs identified (CENTEGIX, Status Solutions, Strongline, Vocera, Singlewire, Rave, Motorola, AtHoc). LLM extraction prompt drafted. Path A (case studies) is 30–45 min focused work. Path B (board minutes, public-district subset) is deferred to v2.5 — harder + lower yield.
3. **Full PII-redacted TAM** — ✓ shipped this session (`data/mart/tam_scored_redacted.csv`, 5,362 rows, 37 cols).

**Other open items (lower priority):**

4. **OSHA state-plan scraper (CA, WA, OR, MD, NC).** Federal SIR dataset excludes state-plan states. Each has its own enforcement portal. Closes the visible gap for Harborview (WA) — currently we use direct news evidence, but state-plan OSHA records would be more authoritative.
5. **IRS 990 narrative grep.** Requires IRS S3 e-file XML + parser (~3-4 hr build). Check if an existing Apify actor does this cleaner.
6. **Weekly refresh loop.** Operational, not portfolio-critical.

---

## Hard rules (from CLAUDE.md — non-negotiable)

1. **Never fabricate.** Unknown fields = `null` + `needs_review=TRUE`. Acute Need proxies must be labeled as proxies.
2. **Public data only. No PHI.** NPPES auth_official is the strongest contact signal used; phone numbers are PII and stripped from committed artifacts.
3. **One-offs only. NEVER email sequences.** The pipeline ends in a rep worklist, not a drip cadence.
4. **Apify + paid contact tools reserved for Tier-A** (the 5 QSOs). Never enrich all 5,362 with paid per-record tools. Stop-and-confirm before any paid run.
5. **Source URLs everywhere.** Every signal carries a `*_source_url`.
6. **The 5 QSOs are the gold standard.** Hand-written briefs > auto-generated ones.
7. **QSO (bench) — Our Lady of the Lake legal posture** — active wrongful-death litigation against incumbent (Inner Parish Security Corp). Do NOT external-send anything referencing that case without Firefly Legal + CRO clearance. Account is benched, not in the v2 5, but kept in `bench/` for reference.

---

## How to run things locally (your Mac, open network)

```bash
# Regenerate end-to-end
python3 skills/seed-tier-c/run.py --all       # ~25 min (cached after first run, all 50 + DC)
python3 skills/forge-score/run.py --all       # ~30 sec (additive max 9 + Standalone cap)
python3 skills/tier-b-osha/run.py --all       # ~5 sec (citation-grade Acute Need lift)
python3 skills/tier-b-incident/run.py --all   # HARD GATE on-site violence classifier
python3 skills/tier-b-incumbent/run.py --all  # Indeed regex vendor detection
python3 skills/tier-b-contracts/run.py --all  # USAspending federal contracts
python3 dashboard/build-data.py               # ~5 sec → dashboard/data.json
cd dashboard && python3 -m http.server 4173   # serve at 127.0.0.1:4173

# Deploy
cd dashboard && npx -y vercel@latest deploy --prod --yes

# Apify (Tier-A only, stop-and-confirm)
python3 skills/qso-linkedin/run.py --ccn 500064          # scrape one QSO
python3 skills/qso-linkedin/run.py --reclassify          # reuse cached scrapes, no Apify cost

# Agents
python3 skills/account-researcher/run.py --ccn 330028
python3 skills/one-off-writer/run.py --ccn 330028
python3 skills/compliance/run.py --state NY
```

Only third-party Python dep is `httpx`. Cached sources (NPPES, Census batches, OSHA SIR ZIP) survive reruns.

---

## File-locations cheat sheet

- Pipeline: `skills/seed-tier-c/run.py` · `skills/forge-score/run.py` · `skills/standalone-score/run.py`
- Tier-B enrichers: `skills/tier-b-{osha,incident,incumbent,contracts}/run.py`
- Agents (LLM): `skills/account-researcher/run.py` · `skills/one-off-writer/run.py`
- Agents (deterministic): `skills/compliance/run.py` · `skills/qso-linkedin/run.py`
- Hand-written QSO briefs (gold standard): `documents/qso-briefs/qso-{1..5}-*.md`
- Portfolio index v2: `documents/qso_briefs.md` (v1 preserved as `qso_briefs_v1.md`)
- Bench (v1 deprecated QSOs): `documents/qso-briefs/bench/`
- Auto artifacts: `documents/qso-briefs/auto/*` (LinkedIn JSONs gitignored) + `auto/_archive/` for stale
- Reference data: `data/reference/{mandates,competitors,coverage-grid,signal-sources}.csv`
- Personas: `context/personas/healthcare-{edm,champion}.md`
- Dashboard: `dashboard/index.html` · builders `build-data.py` + `build-code-tree.py`
- Hard rules + scope: `CLAUDE.md` · methodology: `RUNBOOK.md` · sources: `docs/SOURCES.md`

---

## Collaboration preferences (for the next agent)

- **Verify external sources before committing to a build** — probe the URL/API first; don't over-promise feasibility.
- **Computed truth over engineered targets** — display what the data says; document divergences honestly.
- **Propose → review → implement → commit, per module** — don't one-shot; short proposal, get the nod, then build.
- **AskUserQuestion for decisions, not status updates** — concrete options with tradeoffs.
- **Don't auto-commit** — wait for an explicit "commit" instruction.
- **AI collaboration disclosure stays in README.**

**Session ended:** 2026-06-24 PM · portfolio v2 shipped + Vercel prod current.
