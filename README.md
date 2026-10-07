# Clinical Trial Benchmarking — Peer-Group Audit

A retrospective benchmarking tool for **finished** clinical trials. Given a
trial's design features and its actual duration, it reports where that
duration sits within its peer-group distribution and which design features
are associated with that position.

> **This is not a forecasting tool.** It does not predict trial duration,
> issue a go/no-go verdict, or make causal claims. It is a framing and
> triage instrument for protocol review.

## What it does

1. **Assigns** a finished trial to a deterministic peer group
   (interventional: `stage × scope`; observational:
   `model × perspective`).
2. **Benchmarks** the trial's actual duration against that group's
   empirical distribution — percentile, delta vs median, verdict
   (`unusually fast` → `unusually slow`).
3. **Attributes** the position using per-peer-group SHAP values, splitting
   the explanation into **actionable design levers** vs **contextual
   signals** (era, sponsor, therapeutic area).

## Pipeline

| Notebook | Purpose | Output |
|---|---|---|
| `01_trial_enrollment_data_collection_v3.ipynb` | Chunked collection from ClinicalTrials.gov v2 API | `clinical_trials_major_diseases.parquet` (~542k trials) |
| `02_clinical_trial_peer_grouping_v2.ipynb` | Deterministic peer partition + SHAP attribution | `cluster_data/shared/*.parquet`, `peer_risk_factors.json` |
| `03_clinical_trial_benchmarking_audit_v2.ipynb` | Retrospective audit reports + what-if framing | `audit_output/*.csv`, `*.png` |

## Using the audit

After running notebooks 01 and 02, open
`notebooks/03_clinical_trial_benchmarking_audit_v2.ipynb` and go to
**Cell 11 — "WORKED EXAMPLE"**. This is the primary user entry point.
Three modes are available:

- **Option A** — audit a trial already in the reference corpus.
  Set `_sample_seed` to any integer to pick a different trial.

- **Option B** — audit a trial *not* in the corpus. Fill in the
  `_my_trial` dict with the trial's design features and set
  `_my_actual_duration_days`.

- **Option C** — batch audit one peer group. Set `_batch_peer_group`
  to any key from `peer_dist.index` and cap the run with `_batch_limit`.

Every modifiable line is marked `# ← MODIFY:` with inline notes on
acceptable values. See
[docs/AUDIT_INTERPRETATION.md](docs/AUDIT_INTERPRETATION.md) for how to
read the output.

**Cell 12** extends this with a what-if analysis: it holds the trial's
actual duration fixed and re-benchmarks it against adjacent peer groups.
