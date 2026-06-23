# qso-linkedin — Apify-powered employee enrichment for the 5 QSOs

Uses an Apify actor to pull LinkedIn employee data (name, title, current role)
for **the 5 hand-picked QSO facilities only** per CLAUDE.md Tier-C gate.

## Per CLAUDE.md hard rule

> **Apify and paid contact lookups run ONLY on the 5 QSOs (Tier C). Never enrich
> all 3,000 with paid per-record tools.**

This skill enforces that constraint: it only accepts the 5 known QSO CCNs.
Running on more requires editing `QSO_CCNS` explicitly.

## Source

**Apify LinkedIn Premium Actor** — `harvestapi/linkedin-company-employees`
(or similar). Configurable via `APIFY_LINKEDIN_ACTOR` env var.

- Cost: typically $0.50–$2.50 per company (depends on employee count + result limit)
- For 5 QSOs: probably $3–$12 total
- Apify free tier: $5 credit on signup
- Requires: `APIFY_API_TOKEN` in `.env`

## Output

`documents/qso-briefs/auto/linkedin-<ccn>.json`

Schema:
```json
{
  "ccn": "...",
  "facility_name": "...",
  "linkedin_url": "...",
  "employees": [
    {"name": "...", "title": "...", "headline": "...", "profile_url": "..."}
  ],
  "fetched_at": "..."
}
```

## Buying-committee classification

After scrape, we filter employees to "buying-committee-relevant" roles:
- **EDM candidates**: CEO, COO, EVP Operations, CFO, President
- **Champion candidates**: VP Security, VP Patient Safety, Director Emergency Mgmt, CNO
- **Influencer candidates**: Director Facilities, Director IT, Risk Manager

Output: `documents/qso-briefs/auto/buying-committee-<ccn>.md` with classified table.

## Honest caveats

- LinkedIn URLs are best-guesses; some may be wrong (large systems have multiple
  company pages — flagship hospital vs. parent system)
- Apify actors break periodically when LinkedIn changes its HTML
- Employee data is **as LinkedIn shows it** — current titles may be stale
- Tone: **internal-research only.** Per CLAUDE.md, the QSO 5 (OLOL) work
  has special legal posture — do not external-send anything that surfaces
  named contacts at OLOL until Legal clears.

## Run

```bash
# Single QSO smoke (uses default LinkedIn URL guess)
python3 skills/qso-linkedin/run.py --ccn 500064

# All 5 QSOs
python3 skills/qso-linkedin/run.py --all-qsos

# Override the LinkedIn URL for a CCN
python3 skills/qso-linkedin/run.py --ccn 500064 --url "https://www.linkedin.com/company/..."
```
