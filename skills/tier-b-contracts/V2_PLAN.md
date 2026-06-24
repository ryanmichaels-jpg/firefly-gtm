# tier-b-contracts v2 — execution plan

> Status (2026-06-24 PM): v2 is **scoped and waiting on quota**. SAM.gov key in `.env` is verified valid but daily quota is exhausted (HTTP 429, "You have exceeded your quota. You can access API after 2026-Jun-25 00:00:00+0000 UTC"). The recompete-radar pivot using USAspending alone is buildable now but requires re-pulling period_of_performance fields the v1 cache didn't capture.

## What v2 adds beyond v1

| | v1 (shipped) | v2 (planned) |
|---|---|---|
| Source | USAspending awards (historical) | USAspending + SAM.gov opportunities |
| Time direction | Backward (5-yr lookback) | **Forward — recompete + active opps** |
| Output field | `usa_recipient_name`, `usa_match_confidence` | + `recompete_year`, `recompete_months_out`, `active_opp_count`, `active_opp_first_url`, `active_opp_naics` |
| Signal use | Federal recipient = signal of fed eligibility | **Buying-window = contracts expiring in N months** |

## Path A — USAspending recompete radar (free, no key, executable today)

The current `data/raw/contracts/by-ccn/{ccn}.json` cache captures `Award Amount`, `NAICS`, `Recipient Name`, but **not** `period_of_performance_start_date` / `period_of_performance_current_end_date`. Solution:

1. Update `_search_awards()` in `run.py` to request these fields (they're free — just add to the API `fields` array).
2. Invalidate cache (`rm -rf data/raw/contracts/by-ccn/`) and re-pull.
3. Add `_compute_recompete()`:
   ```python
   def _compute_recompete(awards):
       today = date.today()
       upcoming = []
       for a in awards:
           end = _parse(a.get('Period of Performance Current End Date'))
           if not end or end < today: continue
           months_out = (end - today).days // 30
           if months_out <= 24:  # 2-year radar window
               upcoming.append({'months_out': months_out, 'end': end, 'award_id': a.get('Award ID')})
       upcoming.sort(key=lambda x: x['months_out'])
       return upcoming
   ```
4. Write top-of-list to mart columns: `recompete_year`, `recompete_months_out`, `recompete_award_id`, `recompete_url`.

**Acceptance:** every facility with a recipient match gets either a populated recompete window or null+`recompete_evaluated=True`.

**ETA:** ~30 min focused work (modify queries, blow cache, re-pull, write merger).

## Path B — SAM.gov active opportunities (waiting on quota)

API endpoint that works: `https://api.sam.gov/opportunities/v2/search`. Verified key in `.env` returns 429 ("Message throttled out") today; resets midnight UTC.

Probe to run first thing tomorrow (after midnight UTC):

```bash
KEY=$(grep ^SAM .env | cut -d= -f2 | tr -d '"' | tr -d "'")
curl -s "https://api.sam.gov/opportunities/v2/search?limit=2&postedFrom=05/24/2026&postedTo=06/24/2026&ncode=561612&api_key=$KEY" | python3 -m json.tool
```

If returns 200: probe response shape, find the throttle limit (header `X-RateLimit-Limit`?), decide whether to enrich the curated Tier-B subset or only the 5 QSOs.

Per-facility query strategy:
- NAICS filter: `561612` (security guards), `561621` (security systems), `561690` (other), `334290` (mass-notification gear). See `SAM_NAICS_SECURITY` constant already in `run.py`.
- Lookback: 90 days posted (`SAM_LOOKBACK_DAYS = 90`).
- Match strategy: same recipient-name fuzzy match as USAspending v1 (`MATCH_THRESHOLD_OK = 0.70`). USAspending recipient match is the join key — if a facility already has a USAspending `usa_recipient_name`, use it to filter SAM.gov hits.

Output columns: `active_opp_count`, `active_opp_first_url`, `active_opp_naics`, `active_opp_posted_date`.

## Constants already wired (no new config needed)

In `skills/tier-b-contracts/run.py`:
- `SAM_LOOKBACK_DAYS = 90`
- `SAM_NAICS_SECURITY = ('561612', '561621', '561690', '334290', '541512')`
- `SAM_INTER_REQUEST_DELAY = 1.0`
- `SAM_API = 'https://api.sam.gov'`
- `QSO_CCNS = {...}` matches current portfolio

## Why a recompete radar matters (the GTM story)

Federal contract end dates are **the closest thing to a public RFP/buying-window signal** for hospitals that have any federal procurement footprint. If Mary Washington has a security-services contract ending 2026-09-15, the next 90 days is procurement-active. That's a one-off email subject line by itself: *"Your DLA security contract ends in 4 months — RCW 49.19 starts at the same time."*

## Don't do this in v2

- Don't enrich all 5,362 with paid SAM.gov calls — stop-and-confirm gate stays.
- Don't fabricate recompete_year if period_of_performance is null in the response. Leave null + `needs_review=True`.
- Don't add SAM.gov opportunity URLs to the public dashboard without checking whether they expose sensitive contracting officer names.
