# Data Sources

Every source the Firefly GTM engine reads from, what it gives us, and where it lands. Updated **2026-06-24**.

> **Tier convention** (FLIPPED in v2): Tier C = broad seed (all ~5,362, free), Tier B = curated middle (300–400, free/low-metered), Tier A = the 5 QSOs (paid Apify + hand-validated). v1 had A↔C reversed; everything in this repo now uses the v2 convention.

---

## TL;DR

The engine knows the following about each of the ~5,362 facilities across all 50 states + DC:

- **Identity**: name, CCN, address, parent system, system size
- **Capacity**: beds, ED flag, behavioral health flag, hospital type
- **Risk profile**: safety-net status, teaching-intensity flags (proxies for WPV exposure)
- **Regulatory pressure**: applicable state WPV mandate, status, effective date
- **Geography**: lat/lng
- **Buyer surface**: NPPES authorized_official title (CEO/CFO/etc.)
- **Score**: FORGE total + tier + rationale per dimension

v2 added at-scale signals via tier-b skills (incumbent vendor regex via Indeed, federal contracts via USAspending, on-site violent-incident HARD GATE via news + OSHA SIR). What's still missing at scale: contract expiry, named security champion, building footprint. For the 5 hand-picked QSOs, those gaps are filled by hand-research + Apify LinkedIn in `documents/qso-briefs/`.

---

## 1. Live-pulled sources (Tier-C pipeline = broad seed)

These are what `skills/seed-tier-c/run.py` ingests on every run. Output: `data/mart/tam.csv`.

| # | Source | Endpoint | What we pull | What it tells us | Lands in |
|---|---|---|---|---|---|
| 1 | **CMS Hospital General Information** | data.cms.gov (CSV download) | Facility ID (CCN), name, address, hospital type, ownership, ED flag | Real hospital? Acute care vs. critical access vs. psychiatric? ED present? Government/non-profit/for-profit? | Seed list. `hospital_type`, `ownership`, `has_ED`. |
| 2 | **AHRQ Compendium of US Health Systems** | ahrq.gov (CSV, cp1252) | health_sys_name, health_sys_id, facilities_in_system, hos_majteach, hos_highdpp, hos_highuc | Multi-facility system? System size? Major teaching hospital? High-DSH (safety-net)? High uncompensated care burden? | `parent_system`, `facilities_in_system`, safety-net flags feed FORGE Acute Need. |
| 3 | **CMS Provider of Services (POS)** Q1 2026 | data.cms.gov (CSV, 30 MB) | CRTFD_BED_CNT, PSYCH_UNIT_BED_CNT | Medicare-certified bed count. Psych/behavioral inpatient unit present? | `beds`, `has_behavioral_unit`. Drives FORGE Fit + tier classification. |
| 4 | **NPPES API** | npiregistry.cms.hhs.gov | DBA name, physical address, NPI, authorized_official (name + title + phone) | Marketing/DBA name. Physical (not billing) location. Legal signing officer. | `facility_name` (DBA override), `address`, `edm_seed_*`. Drives FORGE Gravity. |
| 5 | **Census Geocoder API** | geocoding.geo.census.gov | lat, lng | Map placement. | `lat`, `lng`. Powers dashboard map view. |
| 6 | **mandates.csv** (hand-curated) | LegiScan + state statute URLs | mandate_name, status, effective_date per state | Is there a state WPV statute? In force / Upcoming / Enforcement? When? | `mandate_name`, `mandate_status`, `effective_date`. Entire FORGE Event dimension. |
| 7 | **OSHA Severe Injury Reports** | osha.gov bulk ZIP | Employer, EventDate, Nature, Source, NAICS 622 incidents in last 24mo | Citation-grade WPV / staff-injury evidence at the facility. Lifts FORGE Acute Need from AHRQ proxy to documented federal-OSHA evidence. | `osha_severe_injury_count_24mo`, `osha_first_evidence_url`, `osha_first_evidence_date`, `osha_first_evidence_nature`. Lifts `acute_need` 1/2 → 3 for matched facilities. Federal-OSHA-only (5 of our 15 priority states are state-plan, excluded). |

**Run**: `python3 skills/seed-tier-c/run.py --all` · **Cost**: $0 · **Wall-clock**: ~25 min (NPPES is the bottleneck)

## 2. Reference tables (hand-curated, in repo)

Committed lookup tables the pipeline joins against.

| File | What it is | Used by |
|---|---|---|
| `data/reference/mandates.csv` | 87-row WPV statute database with status + effective dates | Phase 7 of seed-tier-a (mandate-join with state-vs-federal precedence) |
| `data/reference/competitors.csv` | 30+ Firefly competitors classified by surface (full-stack/platform/hardware) and role (replace-layer/integrate-layer/frenemy) | Human reference for Tier-B incumbent-vendor matching |
| `data/reference/coverage-grid.csv` + `coverage-grid-ranked.csv` | State-by-state mandate strength ranking | Justifies 15-state scope decision |
| `data/reference/buying-committee.csv` | Healthcare-vertical buying-committee role map | Methodology for Tier-C 5-QSO research |
| `data/reference/signal-sources.csv` | Catalog of external signal sources with cost/cadence | Operational planning |

## 3. One-time external research (the 5 QSO briefs)

Not in the pipeline — done by hand via WebSearch for `documents/qso-briefs/qso-N-*.md`. Every signal carries a public evidence URL inside the brief.

| Source | What it gave us | Which QSOs |
|---|---|---|
| **Regional news** (KIRO 7, Nurse.org, The Advocate, WBRZ, WAFB, KRIS TV) | Dated incident reports (Harborview Feb 2026, OLOL Jackson Mar 2025, Spohn Nov 2024 hoax) | 1, 4, 5 |
| **AHA case studies** | Documented WPV programs at NYP (EMR flagging), OLOL Health Louisiana | 3, 5 |
| **DHS TVTP grantee stories** | NYP's federal grant work on threat assessment training | 3 |
| **HealthLeaders Media** | RWJBarnabas Health's 5-step WPV framework | 2 |
| **Court records / lawsuit filings** (via news) | Jackson v. OLOL & Inner Parish Security Corp wrongful-death suit | 5 |
| **Belleville Patch** (labor news) | 1199SEIU unionization + NLRB filings at Clara Maass | 2 |
| **Seattle PD blotter** | Harborview incident perpetrator details | 1 |
| **LinkedIn profile view** (no scrape) | Heather Runnels confirmed as OLOL nursing executive | 5 |

## 4. Configured but currently blocked / deferred

| Source | Status | Why blocked | Next step |
|---|---|---|---|
| **Competitor customer pages** (CENTEGIX, RF Tech, CenTrak, Status Solutions, Vocera, Singlewire, Rave, Motorola Solutions) | Phase 1 ran — ~5 real names from 18 raw extractions | Vendor pages mostly use image logos / JS-rendered / Cloudflare gates. Text extraction yield fundamentally low. | Lower priority — yield-limited at the source. |
| **Wayback Machine** (Strongline / Securitas Healthcare) | Tested, 404 | URL guess wrong; needs Availability API call to find real snapshot | Quick fix — ~15 min |
| **Google Custom Search Engine** (site:linkedin.com queries) | Code complete, blocked on Google Cloud 403 | Project-level config issue — not resolvable remotely | User needs to sort Cloud account; then `python3 skills/tier-b-techstack/run.py --phase cse` works |
| **OSHA Severe Injury Reports** | ✅ **NOW LIVE** (see source #7 above) | (resolved — URL was at `osha.gov/sites/default/files/January2015toOctober2025.zip`) | Run `python3 skills/tier-b-osha/run.py --all` to re-match. Auto-refresh requires re-downloading the ZIP when OSHA updates it (periodic). |
| **IRS Form 990 narrative** | Probed via ProPublica, ruled out | ProPublica API exposes financial summary only; current PDFs unavailable; needs AWS S3 e-file XML | ~3-4 hrs infra work; lower priority |
| **News incident feeds at scale** | Considered, not built | Free NewsAPI tier doesn't cover 2,353 facilities | **GDELT is the right answer here — free + unlimited** (see "Next" section below) |
| **USA Spending API** | Probed, ruled out | Federal hospital contracts are mostly lab specimens, not security | Not useful — won't pursue |

## 5. Local-only artifacts (gitignored)

| Path | What's there | Why local-only |
|---|---|---|
| `.env` | API credentials (Google CSE key + ID, others as added) | Per `.gitignore` line `.env*` |
| `data/raw/cms-hgi/`, `data/raw/ahrq-compendium/`, `data/raw/cms-pos/`, `data/raw/nppes/`, `data/raw/census-geocode/`, `data/raw/competitor-pages/` | Downloaded source files + caches | Large + NPPES has PII (per-CCN JSON with auth_official phone) |
| `data/staging/*.csv` | Per-step intermediates (01_cms_hgi.csv → 08_tier.csv) | Regenerable from raw |
| `data/mart/tam.csv` and `data/mart/tam_scored.csv` | Full mart with `edm_seed_phone` and full `edm_seed_name` | PII. `tam_scored_sample.csv` is the PII-redacted committable version. |

## Hard rules these sources respect

From `CLAUDE.md`:
1. **Never fabricate.** Unknown fields are `null` + `needs_review=TRUE`.
2. **Public data only. No PHI.**
3. **Every signal carries a `*_source_url`.**
4. **Paid contact tools reserved for Tier-A** (the 5 QSOs) under explicit gate.

## How to regenerate

```bash
# Re-pull + re-score from scratch
python3 skills/seed-tier-c/run.py --all      # ~25 min (broad seed)
python3 skills/forge-score/run.py --all      # ~30 sec (additive max 9 + std cap)
python3 skills/tier-b-osha/run.py --all      # ~5 sec (OSHA SIR lift to citation-grade)
python3 skills/tier-b-incident/run.py --all  # HARD GATE on-site violence classifier
python3 dashboard/build-data.py              # ~5 sec
```

Cached sources (NPPES, Census batches) survive reruns — the only at-scale network operation that re-fires is whatever's missing from cache.
