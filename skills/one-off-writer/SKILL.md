# one-off-writer — LLM-generated first-touch email

Generates an **80-125 word one-off email** for any facility in the scored mart.
Uses Claude Haiku 4.5. Output mirrors the email-draft sections in the 5 hand-written
QSO briefs.

## Per CLAUDE.md hard rule

**ONE-OFFS ONLY. NEVER SEQUENCES.** Each invocation produces ONE email for ONE
person about ONE specific event at ONE hospital. No drip cadence, no `{{first_name}}`,
no automation downstream.

## Run

```bash
python3 skills/one-off-writer/run.py --ccn 450046
python3 skills/one-off-writer/run.py --ccns 500064,310009,330101,450046,190064
```

## Cost

~$0.02–0.08 per email (Haiku 4.5, ~200 token output). 5 emails ≈ $0.15.

## Output

`documents/qso-briefs/auto/one-off-<ccn>-<slug>.md`

Each file contains:
- Recommended To: + CC: lines (role-based; names redacted)
- Subject line
- Email body (80-125 words)
- One-line rationale (why this opening)

## Honest scope

- ✅ Uses real signal stack: mandate, OSHA evidence, beds, parent system, EDM title
- ✅ Voices match Firefly playbook (greenfield / displacement / competitive / scale-out)
- ❌ Does NOT have hand-research insights (e.g., for QSO 5 OLOL, the auto-writer
  doesn't know about the Patricia Jackson lawsuit + Inner Parish Security detail
  — the 5 hand-written briefs include that level of specificity)
- ❌ Does NOT propose CC'd internal stakeholders by name (only roles)

This is the **per-facility** quality bar. The hand-written 5 QSO emails set the
gold standard.
