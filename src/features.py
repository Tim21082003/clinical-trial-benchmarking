"""
Shared feature engineering, encoding/scaling, and selection helpers.

Imported by both 02_clinical_trial_segmentation_v6.ipynb and
03_clinical_trial_forecasting_v2.ipynb, and by 03b_segmentation_experiments.

The two rules that every function here must obey:
  1. Never touch the target column.
  2. Never fit on data outside the training fold passed in.

Any function that violates either rule is a bug, not a design choice.
"""

import ast
import json
import re
import warnings
from typing import List, Tuple, Optional, Dict

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import mutual_info_regression
from xgboost import XGBRegressor

from clinical_trial_forecasting.taxonomy import FEATURE_FAMILIES

warnings.filterwarnings('ignore')


# ============================================================================
# 1. Encoding + scaling (leakage-free)
# ============================================================================

def fit_encode_scale(X_train_raw: pd.DataFrame,
                     X_test_raw: pd.DataFrame
                     ) -> Tuple[pd.DataFrame, pd.DataFrame, RobustScaler, List[str]]:
    """
    Fit one-hot encoding + RobustScaler on TRAIN only, apply to both.

    Aligns test columns to train columns exactly:
      - missing columns -> 0
      - extra columns -> dropped

    Returns
    -------
    X_train_scaled_df, X_test_scaled_df, scaler, encoded_feature_names
    """
    X_train_raw = X_train_raw.copy()
    X_test_raw = X_test_raw.copy()

    for c in X_train_raw.columns:
        if c not in X_test_raw.columns:
            X_test_raw[c] = 0
    X_test_raw = X_test_raw[X_train_raw.columns]

    cat_cols = X_train_raw.select_dtypes(include=['object']).columns.tolist()
    num_cols = X_train_raw.select_dtypes(include=[np.number]).columns.tolist()

    for c in num_cols:
        med = X_train_raw[c].median()
        if pd.isna(med):
            med = 0.0
        X_train_raw[c] = X_train_raw[c].fillna(med)
        X_test_raw[c] = X_test_raw[c].fillna(med)

    for c in cat_cols:
        X_train_raw[c] = X_train_raw[c].fillna('UNKNOWN').astype(str)
        X_test_raw[c] = X_test_raw[c].fillna('UNKNOWN').astype(str)

    if cat_cols:
        X_train_enc = pd.get_dummies(X_train_raw, columns=cat_cols, drop_first=True)
        X_test_enc = pd.get_dummies(X_test_raw, columns=cat_cols, drop_first=True)
    else:
        X_train_enc = X_train_raw.copy()
        X_test_enc = X_test_raw.copy()

    X_test_enc = X_test_enc.reindex(columns=X_train_enc.columns, fill_value=0)

    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train_enc)
    X_test_scaled = scaler.transform(X_test_enc)

    train_df = pd.DataFrame(X_train_scaled,
                            columns=X_train_enc.columns,
                            index=X_train_enc.index)
    test_df = pd.DataFrame(X_test_scaled,
                           columns=X_train_enc.columns,
                           index=X_test_enc.index)

    return train_df, test_df, scaler, X_train_enc.columns.tolist()


def apply_fitted_transform(X_raw: pd.DataFrame,
                           scaler: RobustScaler,
                           feature_names: List[str]) -> pd.DataFrame:
    """
    Apply a pre-fitted scaler to new raw data, aligning to the frozen
    encoded schema. Used at inference time; the training side uses
    fit_encode_scale.
    """
    X_raw = X_raw.copy()

    cat_cols = X_raw.select_dtypes(include=['object']).columns.tolist()
    num_cols = X_raw.select_dtypes(include=[np.number]).columns.tolist()

    for c in num_cols:
        X_raw[c] = X_raw[c].fillna(0.0)
    for c in cat_cols:
        X_raw[c] = X_raw[c].fillna('UNKNOWN').astype(str)

    X_enc = pd.get_dummies(X_raw, columns=cat_cols, drop_first=True)
    X_enc = X_enc.reindex(columns=feature_names, fill_value=0)

    X_scaled = scaler.transform(X_enc.values)
    return pd.DataFrame(X_scaled, columns=feature_names, index=X_raw.index)


# Alias kept for backwards compatibility with existing notebook cells that
# still reference the old name.
encode_and_scale_with_fitted = apply_fitted_transform


# ============================================================================
# 2. Redundancy pruning
# ============================================================================

def prune_correlated_features(X_train: pd.DataFrame,
                              candidates: List[str],
                              target: Optional[np.ndarray] = None,
                              corr_threshold: float = 0.85
                              ) -> Tuple[List[str], pd.DataFrame]:
    """
    Prune redundant features on the TRAINING fold only.

    Two stages:
      1. Family-level: within each FEATURE_FAMILIES group, keep one
         representative (highest MI if target given, else highest variance).
      2. Correlation-cluster: hierarchical clustering on 1 - |spearman|;
         keep one representative per cluster at corr_threshold.

    Returns
    -------
    kept_features : list[str]
    report        : pd.DataFrame with columns
                    [feature, family, pruned_by, kept_representative, mi]
    """
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform

    present = [c for c in candidates if c in X_train.columns]
    if not present:
        return [], pd.DataFrame(
            columns=['feature', 'family', 'pruned_by', 'mi']
        )

    # ---- Stage 1: family-level ----
    family_of = {}
    for fam, members in FEATURE_FAMILIES.items():
        for m in members:
            family_of[m] = fam

    survivors = []
    pruned_rows = []

    for fam, members in FEATURE_FAMILIES.items():
        members_present = [m for m in members if m in present]
        if len(members_present) <= 1:
            survivors.extend(members_present)
            continue

        # Score each member by MI to target (or variance if no target)
        scores = {}
        for m in members_present:
            x = X_train[m].fillna(0).values
            if target is not None:
                try:
                    mi = mutual_info_regression(
                        x.reshape(-1, 1), target,
                        discrete_features=False, random_state=42, n_neighbors=3,
                    )[0]
                except Exception:
                    mi = 0.0
            else:
                mi = float(np.var(x))
            scores[m] = float(mi)

        winner = max(scores, key=scores.get)
        survivors.append(winner)
        for m in members_present:
            if m != winner:
                pruned_rows.append({
                    'feature': m, 'family': fam,
                    'pruned_by': 'family', 'kept_representative': winner,
                    'mi': scores[m],
                })

    # ---- Stage 2: correlation-cluster ----
    standalone = [c for c in present if c not in family_of]

    if len(standalone) > 1:
        X_sub = X_train[standalone].copy()
        # Frequency-encode any object columns so Spearman sees numeric ranks.
        for c in X_sub.select_dtypes(include=['object']).columns:
            X_sub[c] = X_sub[c].map(
                X_sub[c].value_counts(normalize=True)
            ).fillna(0.0)
        X_sub = X_sub.fillna(0)
        corr = X_sub.corr(method='spearman').abs().fillna(0).values
        np.fill_diagonal(corr, 1.0)
        dist = 1.0 - corr
        dist = (dist + dist.T) / 2.0
        np.fill_diagonal(dist, 0.0)

        try:
            Z = linkage(squareform(dist, checks=False), method='average')
            labels = fcluster(Z, t=1.0 - corr_threshold, criterion='distance')
        except Exception:
            labels = np.arange(len(standalone))

        corr_of = dict(zip(standalone, labels))

        cluster_members = {}
        for feat, lab in corr_of.items():
            cluster_members.setdefault(lab, []).append(feat)

        for lab, members in cluster_members.items():
            if len(members) == 1:
                survivors.append(members[0])
                continue

            scores = {}
            for m in members:
                x = X_train[m].fillna(0).values
                if target is not None:
                    try:
                        mi = mutual_info_regression(
                            x.reshape(-1, 1), target,
                            discrete_features=False, random_state=42, n_neighbors=3,
                        )[0]
                    except Exception:
                        mi = 0.0
                else:
                    mi = float(np.var(x))
                scores[m] = float(mi)

            winner = max(scores, key=scores.get)
            survivors.append(winner)
            for m in members:
                if m != winner:
                    pruned_rows.append({
                        'feature': m, 'family': 'correlation_cluster',
                        'pruned_by': 'correlation', 'kept_representative': winner,
                        'mi': scores[m],
                    })
    else:
        survivors.extend(standalone)

    survivors = sorted(set(survivors))
    report = pd.DataFrame(pruned_rows)
    return survivors, report


def compute_vif(X: pd.DataFrame, feature_cols: List[str],
                threshold: float = 10.0) -> pd.DataFrame:
    """
    Variance Inflation Factor for each feature.
    Returns a DataFrame with [feature, vif] sorted descending.
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    present = [c for c in feature_cols if c in X.columns]
    if len(present) < 2:
        return pd.DataFrame({'feature': present, 'vif': [np.nan] * len(present)})

    Xv = X[present].fillna(0).values
    rows = []
    for i, col in enumerate(present):
        try:
            v = float(variance_inflation_factor(Xv, i))
        except Exception:
            v = np.nan
        rows.append({'feature': col, 'vif': v})

    df = pd.DataFrame(rows).sort_values('vif', ascending=False)
    df['flag'] = df['vif'] > threshold
    return df.reset_index(drop=True)


# ============================================================================
# 3. Stability selection
# ============================================================================

def stability_select(X_train: pd.DataFrame,
                     y_train: np.ndarray,
                     candidates: List[str],
                     n_bootstraps: int = 50,
                     n_features: int = 40,
                     min_freq: float = 0.70,
                     max_abs_corr: float = 0.6,
                     random_state: int = 42) -> Tuple[List[str], pd.DataFrame]:
    """
    Bootstrap-based stability selection.

    Runs MI ranking + correlation filtering on n_bootstraps resamples of
    the training fold, keeps features selected in >= min_freq of runs.

    Returns
    -------
    stable_features : list[str]
    freq_table      : pd.DataFrame with [feature, selection_frequency, mean_mi]
    """
    rng = np.random.RandomState(random_state)
    n = len(X_train)

    selection_counts = {c: 0 for c in candidates}
    mi_accum = {c: [] for c in candidates}

    for _ in range(n_bootstraps):
        idx = rng.choice(n, size=n, replace=True)
        Xb = X_train.iloc[idx].reset_index(drop=True)
        yb = y_train[idx]

        # MI on this bootstrap
        scores = {}

        for c in candidates:
            if c not in Xb.columns:
                continue

            s = Xb[c]
            if s.dtype == 'object' or str(s.dtype).startswith('category'):
                # Frequency-encode categoricals to a numeric scalar. This is
                # the cheapest correct fix: it preserves the "how common is
                # this value" signal that MI can consume, and it works for
                # string columns of any cardinality.
                freq = s.map(s.value_counts(normalize=True)).fillna(0.0)
                x = freq.values.astype(float)
            else:
                x = pd.to_numeric(s, errors='coerce').fillna(0.0).values.astype(float)

            try:
                mi = mutual_info_regression(
                    x.reshape(-1, 1), yb,
                    discrete_features=False, random_state=random_state, n_neighbors=3,
                )[0]
            except Exception:
                mi = 0.0
            scores[c] = float(mi)
            mi_accum[c].append(float(mi))

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        def _numeric(col):
            s = Xb[col]
            if s.dtype == 'object':
                return s.map(s.value_counts(normalize=True)).fillna(0.0)
            return pd.to_numeric(s, errors='coerce').fillna(0.0)

        picked = []
        for feat, _ in ranked:
            if any(abs(_numeric(sel).corr(_numeric(feat))) > max_abs_corr
                   for sel in picked):
                continue
            picked.append(feat)
            if len(picked) >= n_features:
                break

        for f in picked:
            selection_counts[f] += 1

    freq_table = pd.DataFrame([
        {
            'feature': c,
            'selection_frequency': selection_counts[c] / n_bootstraps,
            'mean_mi': float(np.mean(mi_accum[c])) if mi_accum[c] else 0.0,
        }
        for c in candidates
    ]).sort_values('selection_frequency', ascending=False).reset_index(drop=True)

    stable = freq_table.loc[
        freq_table['selection_frequency'] >= min_freq, 'feature'
    ].tolist()

        # If too few passed, fall back to top-k by frequency
    if len(stable) < 10:
        import warnings as _w
        _w.warn(
            f"stability_select: only {len(stable)} features passed "
            f"min_freq={min_freq}; falling back to top-{n_features} by frequency."
        )
        stable = freq_table.head(n_features)['feature'].tolist()

    return stable, freq_table


# ============================================================================
# 4. Full per-branch selection pipeline
# ============================================================================

def select_features_per_branch(X_train: pd.DataFrame,
                               y_train: np.ndarray,
                               candidates: List[str],
                               n_features: int = 40,
                               corr_threshold: float = 0.85,
                               max_abs_corr: float = 0.6,
                               n_bootstraps: int = 50,
                               min_freq: float = 0.70,
                               random_state: int = 42
                               ) -> Tuple[List[str], Dict]:
    """
    Two-stage selector: family/correlation prune -> stability select.

    Returns
    -------
    selected : list[str]
    artifacts: dict with keys
        pruned_report, stability_table, kept_after_prune
    """
    # Stage 1
    pruned, prune_report = prune_correlated_features(
        X_train, candidates, target=y_train,
        corr_threshold=corr_threshold,
    )

    if len(pruned) == 0:
        return [], {'pruned_report': prune_report, 'stability_table': None,
                    'kept_after_prune': []}

    # Stage 2
    stable, stab_table = stability_select(
        X_train, y_train, pruned,
        n_bootstraps=n_bootstraps, n_features=n_features,
        min_freq=min_freq, max_abs_corr=max_abs_corr,
        random_state=random_state,
    )

    return stable, {
        'pruned_report': prune_report,
        'stability_table': stab_table,
        'kept_after_prune': pruned,
    }


# ============================================================================
# 5. VIF-augmented guard for the leakage contract
# ============================================================================

def check_no_target_leak(feature_cols: List[str],
                         forbidden: set,
                         raise_on_leak: bool = True) -> List[str]:
    """
    Raise (or return) any feature in `feature_cols` that appears in
    `forbidden`.
    """
    leaked = [f for f in feature_cols if f in forbidden]
    if leaked and raise_on_leak:
        raise ValueError(f"Target leak detected: {leaked}")
    return leaked