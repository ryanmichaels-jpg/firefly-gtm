# account-researcher — automated pre-call brief generation

LLM-powered agent that generates a pre-call brief for any facility in the
scored mart. Uses **Claude Haiku 4.5** (cheap, fast — ~$0.05–0.15 per brief).

Output format mirrors the 5 hand-written QSO briefs in `documents/qso-briefs/qso-N-*.md`:
account snapshot · FORGE rationale · signal narrative · buying committee · open follow-ups.

## When this skill is appropriate

- Researcher generates a brief from **what the engine knows** — mart data, FORGE
  score, OSHA evidence, mandate state. It does NOT pull live news or web data.
- Useful for the next 50-500 facilities beyond the hand-picked 5 QSOs.
- The 5 hand-written briefs remain the gold-standard reference (they include
  things only human research could surface, like the Inner Parish Security
  lawsuit detail at OLOL).

## Honest scope

- ✅ Pulls every column from the scored mart
- ✅ Surfaces FORGE rationale + OSHA evidence with citation URLs
- ✅ Generates buying-committee structure based on NPPES auth_official title
- ❌ Does NOT do web search (no Brave/Google CSE in this build)
- ❌ Does NOT pull news incidents per facility (Tier-B GDELT failed, OSHA covers some)
- ❌ Does NOT name a champion (only EDM from NPPES — champion is Tier-B work)
- ❌ Does NOT identify incumbent vendor (Tier-B failed)

The brief will read as **"here's what the engine knows; here's what would need Tier-B/C enrichment to fill in."** Reviewers see the architecture; never the fabrication.

## Run

```bash
# single facility
python3 skills/account-researcher/run.py --ccn 450184

# multiple
python3 skills/account-researcher/run.py --ccns 450184,500064,310009

# top-N Tier-A
python3 skills/account-researcher/run.py --top 10
```

## Cost

Roughly **$0.05–0.15 per brief** with Haiku 4.5 (small prompt, ~600 token output).
5 QSOs × $0.10 = $0.50. New Anthropic accounts get $5 free credit.

## Output

`documents/qso-briefs/auto/qso-auto-<ccn>-<slug>.md`

Filename pattern keeps auto-generated briefs in their own directory so they're
clearly distinguished from the 5 hand-curated briefs.
