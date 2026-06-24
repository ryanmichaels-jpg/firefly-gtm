# tier-b-incumbent v2 — execution plan

> Status (2026-06-24 PM): v1 (Indeed regex via misceres/indeed-scraper) ships incumbent_primary_vendor for a thin slice. v1's 100% legacy_signal=True on the 5 QSOs is the symptom — Indeed-only misses competitor-published case studies and local integrators. v2 adds two free-compute Apify actors that fill the gap.

## What v2 adds beyond v1

| | v1 (shipped) | v2 (planned) |
|---|---|---|
| Source | Indeed job descriptions (paid Apify) | + vendor case-study pages + hospital-district board minutes |
| Detection | Regex VENDOR_DICTIONARY on JD text | + LLM extraction from case-study text |
| Yield (QSOs) | 0/5 ID'd | Expected 1–3/5 from case studies; 0–2/5 from board minutes |
| Cost | $0.005/result (Indeed scrape) | Free compute (RAG Web Browser + Website Content Crawler) |
| Discrimination | legacy_signal=True is a false positive at v1 — DO NOT use to rank | Multi-source agreement = real incumbent signal |

## Path A — Competitor case-study scrape via RAG Web Browser (free, executable today)

Apify actor: **`apify/rag-web-browser`** — fetches a URL, runs LLM extraction with a prompt, returns structured JSON. Free compute on free tier (~$0.001/page LLM cost).

### Target list (8 vendors with public case-study indices)

| # | Vendor | Case-studies URL | Category | Direct/Adjacent |
|---|---|---|---|---|
| 1 | CENTEGIX | https://centegix.com/customer-stories/ | Wearable duress | Direct |
| 2 | Status Solutions | https://www.statussolutions.com/case-studies/ | Notification | Direct |
| 3 | Strongline (Securitas Healthcare) | https://www.securitashealthcare.com/resources?type=case-study | Wearable duress | Direct |
| 4 | Vocera (Stryker) | https://www.vocera.com/resource-library?type=case-study | Comms badge | Adjacent |
| 5 | Singlewire (InformaCast) | https://www.singlewire.com/customer-stories | Mass notification | Direct |
| 6 | Rave Mobile Safety (Motorola) | https://www.ravemobilesafety.com/customer-stories | Mass notification | Direct |
| 7 | Motorola CommandCentral | https://www.motorolasolutions.com/en_us/about/customer-stories.html | Platform | Adjacent |
| 8 | AtHoc (BlackBerry) | https://www.blackberry.com/us/en/customers | Mass notification | Direct (federal) |

### Extraction prompt (for RAG Web Browser)

```
You are extracting hospital customer references from a security-vendor
case-study page. Return a JSON array of objects:
  [{"hospital_name": "...", "state": "...", "system": "...", "use_case": "...", "case_study_url": "..."}]

Rules:
- Only return care-delivery hospitals (not clinics, not corporate, not non-US).
- If state is not stated, set state to null.
- If the case study URL is on the same page (anchor), include the full
  resolved URL; if not, use the page URL.
- Ignore healthcare orgs that are payers or pharma.
```

### Skill structure

```
skills/tier-b-incumbent/v2_case_studies.py
  - VENDORS = [...] from table above
  - for each VENDORS entry:
      - run apify/rag-web-browser with prompt + URL
      - parse returned JSON
      - persist to data/raw/incumbent-v2/case-studies/{vendor_slug}.json
  - fuzzy-match each extracted hospital_name against data/mart/tam_scored.csv
    (use same name-normalization as tier-b-contracts: strip suffix tokens)
  - emit data/staging/incumbent_v2_matches.csv with columns:
      ccn, vendor, vendor_category, case_study_url, match_confidence
```

### Mart fields written

- `incumbent_case_study_vendor` (top hit)
- `incumbent_case_study_url` (evidence)
- `incumbent_case_study_confidence` (0.0-1.0)
- **Combined-signal field**: `incumbent_signal_strength` = high/medium/low based on count of independent sources agreeing (Indeed v1 + case studies v2 + board minutes v2 + USAspending recipient match)

**ETA:** 30–45 min focused work — actor I/O + matcher + merger.

## Path B — Hospital board minutes via Website Content Crawler (free, harder)

Apify actor: **`apify/website-content-crawler`** — crawls a domain with a regex include filter, returns clean text per page. Free tier.

### Target list (Tier-B subset — public hospital districts / government-owned)

Filter from `data/mart/tam_scored.csv`:
- ownership_type IN ('Government - Local', 'Government - State', 'Government - Federal', 'Government - Hospital District')
- AND state IN ('TX', 'CA', 'WA', 'FL', 'NY', 'IL', 'OR', 'CO', 'AZ', 'MD', 'NC', 'MA', 'NJ', 'LA', 'CT')
- Expected count: ~200–300 facilities

Each public hospital district has a sunshine-law-mandated board-minutes archive on its website. Crawl with include filter `.*(board|minutes|agenda|meeting).*` and extract pages mentioning vendor names.

### Extraction prompt

```
You are reading hospital board meeting minutes. Extract any mention of:
- security or safety vendor names (proper nouns followed by terms like
  "system", "platform", "contract", "RFP", "proposal", "renewal")
- workplace violence prevention program discussions
- security technology budget approvals

Return JSON: {"vendors_mentioned": [...], "wpv_program_mentioned": bool,
              "security_capex_mentioned": bool, "context_snippet": "..."}
```

### Why this is harder than case studies

- Board minutes are typically PDFs, not HTML — needs PDF extraction (Website Content Crawler does it but inconsistently).
- Sunshine laws vary — some districts publish only summary, not full text.
- Vendor mentions in minutes are often non-incumbent (RFP discussions of *potential* vendors).
- Local integrators (e.g., Tyco Integrated Solutions) get named more than national platforms.

**Recommendation: defer Path B to v2.5.** Path A alone is 30-45 min and meaningfully lifts the discriminating power.

## Why this matters (the GTM story)

The v1 `legacy_signal=True` flag is a known false positive — "no signal" doesn't mean "no incumbent", it means "we didn't look in the right places." A confirmed competitor case-study match is the single highest-quality signal for a replace-layer pitch: *"Hospital X chose CENTEGIX in 2022. They're on a 5-yr contract. RCW 49.19 starts 2026-01-01. Here's why we're different."*

## Don't do this in v2

- Don't fabricate vendor names if the page returns ambiguous content. Leave null + `needs_review=True`.
- Don't use case-study quotes in outbound copy without permission — they're vendor marketing.
- Don't run Path B on private/Catholic systems — board minutes aren't required to be public.
- Don't reward integrate-layer-only matches (cameras/VMS/access) — per CLAUDE.md, those are neutral signals, not green flags. The `replace_layer` filter in `VENDOR_DICTIONARY` already encodes this.
