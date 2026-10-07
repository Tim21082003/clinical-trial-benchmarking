# Methodology

How trials are grouped, benchmarked, and attributed. This document
describes the pipeline's construction; [AUDIT_INTERPRETATION.md](AUDIT_INTERPRETATION.md)
describes how to read its output.

---

## 1. Scope

This is a **retrospective peer-group benchmarking audit** for finished
clinical trials. Given a trial's design features and its *actual*
duration, the pipeline reports:

- where that duration sits within its peer-group distribution,
- which design features are associated with that position.

It does not predict, forecast, or issue go/no-go verdicts.

---

## 2. Corpus

- **Source:** ClinicalTrials.gov v2 API.
- **Query:** conditions matching any of 223 terms across 18 therapeutic
  areas (`THERAPEUTIC_AREA_EXTENDED` in `taxonomy.py`).
- **Size:** ~542,000 records collected; ~171,900 survive duration
  filtering.
- **Branches modeled:** `INTERVENTIONAL` and `OBSERVATIONAL` only.
  `EXPANDED_ACCESS` and others are dropped before partition.

---

## 3. Peer partition (Strategy A)

Peer groups are assigned by a **deterministic** function — no clustering,
no randomness. Same design features always map to the same peer group.

### Interventional

    <stage>::<scope>

| Axis | Values | Derivation |
|---|---|---|
| stage | `unphased`, `exploratory`, `pivotal`, `confirmatory` | from `phase_score`: 0→unphased, 1→exploratory, 2→pivotal, 3/4→confirmatory |
| scope | `unknown`, `single-site`, `regional`, `multinational` | from `(num_sites, num_countries)`; `(0,0)` → `unknown` (not `single-site`) |

### Observational

    obs::<model>::<perspective>

| Axis | Values |
|---|---|
| model | `cohort`, `case-control`, `case-only`, `case-crossover`, `ecologic`, `family-based`, `other` |
| perspective | `prospective`, `retrospective`, `cross-sectional`, `other` |

Raw CT.gov enums are normalized via `OBSERVATIONAL_MODEL_MAP` and
`OBSERVATIONAL_PERSPECTIVE_MAP`; unrecognized values fall to `other`.

### Coverage

- **44** peer groups total.
- **39** reliable (`n ≥ 30`).
- **5** unreliable groups fall back to a coarser key at audit time
  (`obs::<model>` for observational; `<stage>` or `::<scope>` for
  interventional, whichever has more trials).

### Separation gate

The partition must clear an eta-squared threshold on log-duration:

- Interventional: **η² = 0.0469**
- Observational: **η² = 0.0469**
- Threshold: **0.03**

A failing gate does not halt the pipeline; it flags that peer group
explains little duration variance in that branch.

---

## 4. Attribution model (SHAP)

A single global XGBoost regressor is fit on the train fold to produce
per-peer-group SHAP attributions.

| Setting | Value |
|---|---|
| Model | `XGBRegressor` |
| `n_estimators` | 300 |
| `learning_rate` | 0.04 |
| `max_depth` | 6 |
| Target | `log1p(duration_days)` |
| Features | 107-column audit pool, one-hot encoded |
| Fit scope | Train fold only (80% / 20% split, seed 42) |

### Reported quality

| Metric | Value |
|---|---|
| R² (train) | 0.4134 |
| R² (test) | 0.3819 |
| Gap | **+0.0316** |

A gap above 0.10 triggers an inline overfitting warning in every audit
report. The current gap does not.

### What SHAP means here

SHAP values are computed **per peer group** on the full corpus. Each
feature's mean signed SHAP value inside a group determines its
`direction`:

- `+` → feature value is associated with **longer** durations in that group
- `−` → associated with **shorter** durations in that group

The sign can flip between peer groups. A gloss is stored per
`(feature, direction)` pair, not per feature.

---

## 5. Feature categorization

Every audit feature is assigned to one category (`FEATURE_CATEGORY` in
`taxonomy.py`), used to split the audit report into two blocks:

| Category | Meaning | Example |
|---|---|---|
| `design_lever` | Sponsor-controlled at protocol design | `num_sites`, `enrollment_count` |
| `era_cohort` | When the trial ran | `years_since_registration` |
| `sponsor` | Who ran it | `funding_industry` |
| `therapeutic_area` | What it studies | `is_oncology` |
| `text_context` | Eligibility-text-derived | `elig_text_word_count` |
| `other` | Fallback | — |

Categorization is a **display aid**, not a partition key. It does not
affect the model, the SHAP values, or the ranking.

---

## 6. Temporal proxy

`years_since_registration` uses a **frozen reference date**, persisted to
`cluster_data/shared/temporal_reference.json` on first run and read back
on every subsequent run. This keeps the scalar comparable across
retrains. The reference is the max `start_date` observed in the training
fold, guarded against implausible future dates (ceiling = run date).

---

## 7. Reproducibility guarantees

- **Deterministic peer assignment.** The audit harness re-derives
  `regime_bucket` on a 1,000-trial sample and asserts zero mismatches
  against the persisted assignments.
- **Byte-identical partition helper.** `build_strategy_A_partition` is
  duplicated in notebooks 02 and 03; notebook 02's Cell 10 asserts the
  diagnostic and shipped partitions agree on all rows.
- **Reproducible audits.** `audit_trial()` on the same trial produces
  identical output, excluding the `generated_at` timestamp.
