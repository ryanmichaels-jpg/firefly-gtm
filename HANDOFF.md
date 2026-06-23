# Firefly GTM Engine — session handoff (2026-06-23, PM)

> **Supersedes the morning `a4af8d0e-context.md` handoff.** Read this + `CLAUDE.md` + everything in `context/` before running any skill.
> This handoff was written in a Claude Code **web** session that turned out to be network-locked (see below). We are **moving back to local Claude Code** in your terminal. Everything you need is already on your Mac.

---

## TL;DR

Ryan Michaels (ex-SDR/AE → GTM Engineer) is building a real working GTM engine as a portfolio + interview-prep artifact for **Firefly** (AI + IoT physical-safety platform — Ember software + Lattice hardware, sells into mandate-driven healthcare).

Repo: `~/Projects/firefly-gtm` · GitHub: https://github.com/ryanmichaels-jpg/firefly-gtm · Live dashboard: https://dashboard-steel-omega-96.vercel.app

**9 Firefly commits in.** Shipped: 15-state TAM seed (2,353 hospitals), F.O.R.G.E. scoring (622 Tier-A), 5 hand-picked QSOs with briefs + one-offs, OSHA SIR enrichment (106 tagged, 59 lifted to citation-grade Acute Need), 4 working agents, single-file dashboard deployed to Vercel.

---

## ⚠️ READ FIRST — why we're working locally, not in the cloud

A Claude Code **web** session runs in an ephemeral cloud container with a restricted **network policy**. We confirmed this session could reach **only** GitHub, the Anthropic API, and package registries (npm/pip/cargo). **Every GTM data source and Apify returned 403 from the proxy gateway** — CMS, NPPES, AHRQ, Census, OSHA, ProPublica, `api.apify.com`. Verified in the proxy's own failure log.

On top of that, the full data + secrets are **local-only and never pushed** (see next section). So the cloud session had neither the network nor the data to do the real work. **Local Claude Code on your Mac has both** — open network, the data, the `.env`, the uncommitted skills, the cached Apify scrapes. That's why we switched.

If you ever DO want the cloud session to work: relaunch the web environment with full outbound network (or an allowlist of `data.cms.gov`, `npiregistry.cms.hhs.gov`, `www.ahrq.gov`, `geocoding.geo.census.gov`, `www.osha.gov`, `api.apify.com`, `api.anthropic.com`), set `ANTHROPIC_API_KEY` + `APIFY_API_TOKEN` as env vars, add `pip install httpx` as a setup script, and upload `data/mart/tam*.csv` + the 5 `documents/qso-briefs/auto/linkedin-*.json`. But local is easier for an active build.

---

## What "local-only data" means (this tripped up the web session)

The pipeline writes the full mart to `data/mart/tam.csv`, which contains PII — `edm_seed_name` + `edm_seed_phone`. So it's **gitignored** (`.gitignore:33`) and **never pushed**. Same for `data/raw/` (cached source pulls), `data/mart/tam_scored.csv`, and `.env`. They live **only on your Mac**. GitHub (and any fresh clone) has just the PII-redacted samples: `data/mart/tam_sample.csv` + `tam_scored_sample.csv` (170 rows).

Two **uncommitted experimental skills** — `skills/tier-b-news/` and `skills/tier-b-techstack/` — also exist **only in your local working tree** (never committed/pushed). If you want them, they're on your Mac.

---

## Working tree state

```
Branch for in-progress work:   claude/fervent-archimedes-6nz0tk (this handoff is committed here)
GitHub (public):               9 Firefly commits on top of 3 starter-kit base commits
Local-only (your Mac, gitignored): data/mart/tam.csv + tam_scored.csv (PII) · data/raw/ caches ·
                               .env (4 keys) · skills/tier-b-news/ + skills/tier-b-techstack/ (uncommitted) ·
                               documents/qso-briefs/auto/{linkedin-*.json, buying-committee-*.md} (PII)
Committed (PII-redacted):      tam_sample.csv, tam_scored_sample.csv, dashboard/data.json
```

**Anthropic tier cap was bumped (per Ryan, night of 2026-06-22).** The earlier rate-limit-until-July-1 note is now resolved — `account-researcher` + `one-off-writer` can run again. (They read `data/mart/tam_scored.csv`, so run them where that file lives — your Mac.)

---

## What's shipped (verified against the repo this session)

| Area | State |
|---|---|
| TAM seed | 15-state pipeline, 2,353 hospitals (`skills/seed-tier-a/run.py`) |
| FORGE scoring | 622 Tier-A scored; tiers A/B/C/X (`skills/forge-score/run.py`) |
| 5 QSOs | hand-written briefs `documents/qso-briefs/qso-1…5-*.md` + auto briefs/one-offs in `auto/` |
| OSHA enrichment | `skills/tier-b-osha/run.py` — 106 tagged, 59 lifted to citation-grade Acute Need |
| 4 agents | account-researcher · one-off-writer · compliance · qso-linkedin |
| Compliance docs | 14 states, `documents/compliance/` |
| Dashboard | `dashboard/index.html` (single file) + data.json (PII-redacted) + code.json |
| Reference data | mandates · competitors · coverage-grid(-ranked) · buying-committee · signal-sources |
| Docs | `docs/SOURCES.md` · `RUNBOOK.md` · `ARTICLE.md` · `diagrams/source-map.svg` |

---

## Contact data — the real picture (asked about directly)

There are **two tiers of contact data**, and they are very different:

**Tier 1 — broad + shallow: the NPPES `authorized_official` ("edm_seed").** Pulled free during the seed pipeline. It's **name + title + phone — no email.**
- Coverage (from the committed 170-row scored sample): **127/170 (75%) have a title.** By FORGE Gravity in the sample: gravity 3 (exec-title) = 62 (36%), gravity 1–2 (non-exec/partial) = 65, gravity 0 (none) = 43. Exact full-TAM counts are in your local `tam.csv`; ~75% is the sample rate for scored Tier-A.
- **Who:** the legal signing officer on the NPI record — typically **CEO / CFO / President / COO / Administrator** (sometimes a compliance or credentialing coordinator). Top raw titles: CFO / Chief Financial Officer (most common), CEO, President, COO.
- It is a **proxy for the org decision-maker, NOT a verified security buyer**, and has **no email**. Feeds FORGE Gravity.

**Tier 2 — narrow + deep: the 5 QSOs only.** Via the Apify LinkedIn actor (`harvestapi~linkedin-company-employees`, "Full $8/1k" mode, ≤100 employees) + hand research → real **role-mapped buying committees** (champion = security/safety/EM; EDM = C-suite; influencers = facilities/IT/risk). Artifacts (`buying-committee-*.md`, `linkedin-*.json`) are **PII-gitignored, local-only.** This is where real names surfaced — e.g. **Mark Mac Donnell, NYP Security Director.**

**Honest bottom line:** only **5 organizations** have a real, named, role-mapped buying committee. The other ~600 scored accounts have, at best, an org-level name+title+phone proxy and **zero emails**. Closing that gap at scale was `tier-b-techstack`'s job (and what it couldn't deliver at the source).

---

## The 5 QSOs + the re-pick option (Ryan is reconsidering these)

Current five (all `forge_total=27`, the max = Fit × Acute 3 × Event 3 × Gravity 3):

| # | Facility | State | Beds | System | Mandate | Play |
|---|---|---|---|---|---|---|
| 1 | Harborview Medical Center | WA | 413 | UW Medicine | RCW 49.19 — In force | Feb 14 2026 ED rampage ($100K) → enforcement clock |
| 2 | Clara Maass Medical Center | NJ | 472 | RWJBarnabas | N.J.S.A. 26:2H-5.17 — In force | RWJB 5-step framework + 1199SEIU pressure |
| 3 | NewYork-Presbyterian | NY | 2,262 | NYP | Ch.618/2025 — Upcoming 2027-01-01 | TVTP playbook → scale-out before deadline |
| 4 | CHRISTUS Spohn — Corpus Christi | TX | 1,040 | CHRISTUS | SB240 — In force | Nov 13 2024 dementia hoax — 50 officers, false-alarm cost |
| 5 | Our Lady of the Lake | LA | 976 | FMOL | Lynne Truxillo Act — In force | Two homicides + named-incumbent lawsuit (⚠️ legal posture) |

**Selection criteria** (applied to the forge=27 pool): forge_total=27, exec-title EDM, + diversity across state / system / mandate-status / geography / story type.

**Re-picking is cheap** — it's a re-rank + re-select over `tam_scored.csv`, then regenerate briefs for any swaps. The pool is deep: the 170-row sample alone has **32 facilities tied at forge=27** (the full local set is larger). Other 27-scorers seen just in the sample, as swap candidates: Banner–UMC Phoenix (AZ), Tucson Medical (AZ), University of Colorado Hospital (CO), Ochsner Medical Center (LA), University Medical Center New Orleans (LA), Montefiore (NY), Nassau University MC (NY), Newark Beth Israel (NJ), Jamaica Hospital (NY), Riverside Community (CA), and more.

---

## The finish list (prioritized for the next session)

1. **Wire in Ryan's new contracts Apify actor** — scrapes incumbent **contracts + expiry dates**. This is high-leverage: `contract_expiry` is a real FORGE Event/timing signal and directly feeds "when is this account in-cycle." Build a skill modeled on `skills/qso-linkedin/run.py` (Tier-C gate, cache-then-reclassify, `*_source_url` on every cell). **Need from Ryan: the actor ID + a sample input payload + sample output JSON** so the field mapping is exact.
2. **OSHA state-plan scraper (CA/WA/OR/MD/NC)** — the federal SIR dataset excludes state-plan states, which is why **QSO-1 Harborview has no OSHA evidence.** Each state has its own enforcement portal. Closes the most visible QSO gap. Also worth checking OSHA's full establishment/inspection search, not just SIR.
3. **IRS 990 narrative feasibility** — ProPublica only exposes financial summaries (already ruled out). Real path: IRS 990 **e-file XML on AWS S3** + a parser to grep safety/security program narrative. Verify the source has full-text 990s before committing (~3–4 hr build). Check whether an Apify actor does this cleaner before building from scratch.
4. **Re-pick the 5 QSOs** if desired (see pool above).
5. **Carryover deferrals** (lower priority): unblock `tier-b-techstack` Phase 3 (Google CSE 403 — Google Cloud project config, Ryan-side), `tier-b-news` GDELT noise problem, README `_deploy URL — pending push_` placeholder (`README.md:13`), redact `buying-committee-*.md` to titles-only for committable versions.

---

## The two uncommitted `tier-b` skills (what they're for)

| Skill (Mac-only, uncommitted) | Goal | Status |
|---|---|---|
| `tier-b-techstack` | Detect each hospital's **incumbent security vendor** at scale + Google-CSE LinkedIn phase for named contacts. Tells you replace-layer (duress/notification = green flag) vs integrate-layer (cameras/access = neutral). | Low yield (~5 names from 18 raw — vendor pages use image logos / Cloudflare / JS SPAs). CSE phase blocked on Google Cloud 403. |
| `tier-b-news` | Pull **recent incident/violence news per facility** at scale via GDELT → populates Acute Need beyond OSHA. | Noise-dominated (matched OLOL to a Mall of Louisiana shooting) + GDELT rate limits/429s. |

---

## Hard rules (from CLAUDE.md — non-negotiable)

1. **Never fabricate.** Unknown fields = `null` + `needs_review=TRUE`. Acute Need proxies must be labeled as proxies.
2. **Public data only. No PHI.** NPPES auth_official is the strongest contact signal used; phone numbers are PII and stripped from committed artifacts.
3. **One-offs only. NEVER email sequences.** The pipeline ends in a rep worklist, not a drip cadence. No `{{first_name}}`.
4. **Apify + paid contact tools reserved for Tier-C (the 5 QSOs).** Never enrich all 2,353 with paid per-record tools. Stop-and-confirm before any paid run.
5. **Source URLs everywhere.** Every signal carries a `*_source_url`.
6. **The 5 QSOs are the gold standard.** Hand-written briefs > auto-generated ones.
7. **QSO 5 (Our Lady of the Lake) legal posture** — active wrongful-death litigation against incumbent (Inner Parish Security Corp). Do NOT external-send anything referencing that case without Firefly Legal + CRO clearance.

---

## How to run things locally (your Mac, open network)

```bash
# Regenerate the dashboard from scratch
python3 skills/seed-tier-a/run.py --all      # ~25 min (cached after first run)
python3 skills/forge-score/run.py --all      # ~30 sec
python3 skills/tier-b-osha/run.py --all      # ~5 sec
python3 dashboard/build-data.py              # ~5 sec
python3 dashboard/build-code-tree.py         # ~2 sec
cd dashboard && python3 -m http.server 4173  # serve at 127.0.0.1:4173

# Agents (Anthropic cap now bumped; read tam_scored.csv)
python3 skills/account-researcher/run.py --ccn 450046
python3 skills/one-off-writer/run.py --ccn 450046
python3 skills/compliance/run.py --state WA
python3 skills/qso-linkedin/run.py --ccn 500064            # Apify (Tier-C only)
python3 skills/qso-linkedin/run.py --reclassify            # reuse cached scrapes, no Apify cost
```

Only third-party Python dep is **`httpx`** (everything else is stdlib). Cached sources (NPPES, Census batches) survive reruns.

---

## File-locations cheat sheet

- Pipeline: `skills/seed-tier-a/run.py` · `skills/forge-score/run.py` · `skills/tier-b-osha/run.py`
- Agents (LLM): `skills/account-researcher/run.py` · `skills/one-off-writer/run.py`
- Agents (deterministic): `skills/compliance/run.py` · `skills/qso-linkedin/run.py`
- Hand-written QSO briefs (gold standard): `documents/qso-briefs/qso-N-*.md`
- Auto artifacts: `documents/qso-briefs/auto/*` (LinkedIn ones PII-gitignored)
- Reference data: `data/reference/{mandates,competitors,coverage-grid,coverage-grid-ranked,buying-committee,signal-sources}.csv`
- Personas (buying-committee source of truth): `context/personas/healthcare-{edm,champion}.md`
- Source inventory + honest deferrals: `docs/SOURCES.md`
- Dashboard: `dashboard/index.html` · builders `dashboard/build-data.py` + `build-code-tree.py`
- Hard rules + scope: `CLAUDE.md` · methodology: `RUNBOOK.md`

---

## Cost summary (cumulative ~$4.05)

| Source | Spent | Notes |
|---|---|---|
| All public-data pulls (CMS/AHRQ/NPPES/Census/mandates/OSHA SIR) | $0 | free, no key |
| Anthropic Haiku 4.5 (5 briefs + 5 one-offs) | ~$0.05 | cap now bumped |
| Apify LinkedIn (5 QSOs × ~$0.80) | ~$4.00 | "Full" $8/1k mode |

---

## Collaboration preferences (for the next agent)

- **Verify external sources before committing to a build** — probe the URL/API first; don't over-promise feasibility. (GDELT, OSHA URL hunt, CSE all burned this.)
- **Computed truth over engineered targets** — display what the data says; document divergences honestly.
- **Propose → review → implement → commit, per module** — don't one-shot; short proposal, get the nod, then build.
- **AskUserQuestion for decisions, not status updates** — concrete options with tradeoffs.
- **Don't auto-commit** — wait for an explicit "commit" instruction.
- **AI collaboration disclosure stays in README.**

---

## First moves for the new local session

1. Confirm you're in `~/Projects/firefly-gtm` with the data present: `ls data/mart/tam.csv data/mart/tam_scored.csv .env`
2. Decide branch strategy — this handoff is on `claude/fervent-archimedes-6nz0tk`; pick where to continue work.
3. Have the **contracts Apify actor ID + sample I/O** ready — that's the #1 build and the field mapping needs the real output shape.
4. Decide whether the 5 QSOs stay or get re-picked from the forge=27 pool.

**Session ended (web):** 2026-06-23 · moving to local Claude Code.
