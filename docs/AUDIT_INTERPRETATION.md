# How to Read an Audit Report

A practical guide to `render_audit_report()` output. Construction details
live in [METHODOLOGY.md](METHODOLOGY.md).

The audit is **descriptive**. It answers *"how does this trial compare to
its peers?"*

---

## Report anatomy
TRIAL AUDIT REPORT
Trial: NCT07730294
Peer group: pivotal::single-site
Peer group size: 12,465 trials

── DURATION ───────────────────
Actual duration: 731.0 days (2.00 years)
Peer median: 1,065.0 days
Peer p05 / p95: 182.0 / 3,256.8 days
Peer p10 / p90: 274.0 / 2,557.0 days

Percentile in peers: 34.7% 
Delta vs peer median: -334.0 days (-31.4%)

── VERDICT ───> TYPICAL

── ACTIONABLE FEATURES (design levers) ─────────────────────
[design ] enrollment_count -0.0851 =75.0
↳ Larger enrollment targets are associated with shorter
durations in this peer group.

── CONTEXTUAL FEATURES (not design levers) ─────────────────
[era ] years_since_registration +0.2076 =0.1670
[ta ] is_oncology +0.1626 =0
[sponsor] funding_industry +0.1620 =False


---

## DURATION block

- **Actual duration** — the trial's real elapsed days.
- **Peer median** — the 50th percentile of peer durations.
- **p05/p95, p10/p90** — the middle 90% / 80% band of peers.
- **Percentile** — fraction of peers that ran *strictly shorter*.
  `34.7%` means faster than ~35% of peers.
- **Delta vs median** — signed difference from the peer median.

The bar is a rendering aid, not a statistic.

---

## VERDICT bands

| Percentile | Verdict |
|---|---|
| < 5 | `unusually fast` |
| 5 – 25 | `fast` |
| 25 – 75 | `typical` |
| 75 – 95 | `slow` |
| > 95 | `unusually slow` |

Convention, not a hypothesis test. `typical` spans the middle half, a
wide band. Do not treat `slow` as "failure" or `unusually fast` as
"good design".

---

## Peer-group lines

| Line | Meaning |
|---|---|
| `Peer group size: 12,465 trials` | Solid benchmark. |
| `Peer group size: 45 trials ⚠️ LOW-CONFIDENCE` | Thin benchmark; percentile is noisy. |
| `Peer group: obs::case-control` (coarse key) | Exact group had < 30 trials; audit used a fallback key. Deliberate trade of resolution for stability. |

---

## Attribution blocks

Two blocks, ordered by `|SHAP|` descending. Same list, partitioned by
category — the split does not re-rank.

Line format:
[<label>] <feature> <sign><shap> =<value>


- `[design ]` — padded category label; `[design ]` ≡ `[design]`.
- `-0.0851` — signed mean SHAP.
- `=75.0` — the trial's value; `=nan` if missing.
- `↳ ...` — gloss: what the sign means *in this peer group*.

### How to read SHAP

- `+` → feature value associated with **longer** durations in this group.
- `−` → associated with **shorter** durations.
- Magnitude is **relative to the peer group**, not a coefficient and not
  comparable across groups.

### The `=nan` case

Feature is missing for this trial. The attribution still renders (the
model imputed a median), but do not draw a conclusion from a value you
do not have.

### The empty actionable block

When no design lever ranks in the peer group's top features:
(No design levers ranked in this peer group's top features.)
This trial's position is driven primarily by context —
era, sponsor, or therapeutic area — not by design choices.

This is a **finding**, not a bug. It means the audit cannot offer an
actionable lever for this group.

### Category labels

| Label | Category | Controllable? |
|---|---|---|
| `[design]` | Design lever | Yes — set at protocol design |
| `[era]` | Registration era | No |
| `[sponsor]` | Sponsor type | No |
| `[ta]` | Therapeutic area | No |
| `[text]` | Eligibility-text context | Partly |
| `[other]` | Uncategorized | — |

---

## Confidence warnings

Two warnings can appear above the attribution blocks. Both are silent by
default on the shipped model.

⚠️ Attribution model gap (train-test) = +0.1234
Read the rankings below as directional, not precise.

Fires when the train–test R² gap exceeds **0.10**. Current model:
gap = **+0.0316**, so this warning does not fire.

⚠️ Attribution model R²(test) = 0.1234 — below the informative floor.
Rankings are descriptive, not diagnostic.

Fires when held-out R² drops below **0.20**. Current model:
R²(test) = **0.3819**, so this warning does not fire.

**No warning ≠ precise.** The current model explains ~38% of variance
in log-duration. Read rankings as directional signals throughout.

---

## Worked interpretation

Trial: NCT00710983
Peer group: unphased::single-site (42,265 trials)
Actual duration: 2,375.0 days (6.50 years)
Peer median: 790.0 days
Percentile in peers: 92.6%
Verdict: SLOW

[design ] enrollment_count -0.1028 =nan
[design ] us_percentage +0.0681 =0.0
[era ] years_since_registration -0.1866 =18.25
[sponsor] funding_industry +0.1306 =False
[ta ] is_oncology -0.0915 =0


1. **Position.** Ran 6.5 years; peers median 2.2 years; 93rd percentile.
   `slow`, just under `unusually slow`.
2. **Attribution.** Top signal is `years_since_registration` at `−0.1866`
   — older registrations correlate with *shorter* durations here. This
   trial is 18.25 years old, so the signal points toward speed, not
   slowness. Context, not a lever.
3. **Levers.** `enrollment_count` is missing (`=nan`). `us_percentage`
   is `0.0` and its sign says higher US share → longer, so with zero US
   sites this lever also points toward speed.
4. **Net read.** The trial ran slow despite design features and context
   that the model associates with fast trials. Something the corpus does
   not capture — execution, site performance, amendments, regulatory
   delay — likely drove the duration.

**Do not read this as** *"more enrollment would have saved 2 years."*
The audit does not support that.

---

## Comparing two audits

When the same trial is benchmarked against two peer groups (the what-if
cell in notebook 03):

1. **The actual duration is fixed.** Only the reference distribution
   changes. A `slow` → `typical` shift means the yardstick changed, not
   the trial.
2. **SHAP magnitudes are not cross-comparable.** Compare rank order
   within a group, not magnitude across groups.
3. **`typical` is wide.** Percentile 26 and 74 both read `typical`; the
   durations may differ by a year.

Sort what-if tables by verdict severity, not percentile.

---

## Anti-patterns

| Misreading | Why it's wrong |
|---|---|
| "Slow trial → bad design choices." | Slow is relative to peers, not to an ideal. |
| "SHAP −0.10 → 10% savings." | SHAP is an attribution in log-duration space, not a coefficient. |
| "`typical` means the trial is fine." | `typical` spans p25–p75. It means unremarkable, not well-run. |
| "Group A's SHAP > Group B's → A matters more." | Magnitudes are scaled per group. |
| "`unusually fast` → copy the design." | Fast may reflect short follow-up, early termination, or a lower endpoint bar. |
| "`=nan` means the feature doesn't matter." | The value is missing for *this trial*. The feature may rank high for the group. |
| "No warning → attributions precise." | Warnings fire only past fixed thresholds. R² ≈ 0.38 is the ceiling. |

---

## Good for / not for

**Good for**
- Triaging a portfolio for unusually long/short trials.
- Framing protocol review: *"what peer median are we signing up against?"*
- Checking whether a `slow` verdict is an artifact of a tight peer group.
- Post-mortem: flagging trials whose position no visible lever explains.

**Not for**
- Predicting whether an ongoing trial will finish on time.
- Comparing sponsor quality.
- Judging trial success or failure.
- Causal claims about design levers.
- Any regulatory, clinical, or investment decision.

---

## Quick reference
VERDICT BANDS
<5 unusually fast · 5–25 fast · 25–75 typical · 75–95 slow · >95 unusually slow

SHAP

longer · − shorter · magnitude is group-relative, not cross-comparable

WARNINGS (silent by default; current gap = +0.0316)
gap > 0.10 directional, not precise
R²(test) < 0.20 descriptive, not diagnostic

NOT SUPPORTED
prediction · causality · cross-group SHAP · success judgment
