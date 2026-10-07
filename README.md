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
