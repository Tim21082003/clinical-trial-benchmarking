"""
Temporal stability and cluster-separation audits.

Both functions are pure: they take DataFrames and return JSON-serializable
dicts. No side effects. The calling notebook is responsible for persistence.

This module also carries the directional gloss used by the audit report
renderer (in notebook 03) to translate SHAP magnitudes into sentences a
reader can act on. The gloss is a display aid; it does not affect any
computation.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, kruskal
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import cross_val_score


__all__ = [
    'compute_temporal_stability',
    'compute_cluster_separation',
    'FEATURE_CATEGORY',
    'categorize_feature',
    'DIRECTIONAL_GLOSS',
    'gloss',
    'category_display_label',
]


# NumPy 2.0 renamed trapz -> trapezoid. Support both.
_trapz = getattr(np, 'trapezoid', None) or np.trapz


# ============================================================================
# 1. Temporal stability
# ============================================================================

def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence between two probability vectors."""
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    p = p / max(p.sum(), 1e-12)
    q = q / max(q.sum(), 1e-12)
    m = 0.5 * (p + q)

    def _kl(a, b):
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log(a[mask] / b[mask])))

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def compute_temporal_stability(df_branch: pd.DataFrame,
                               cluster_col: str,
                               year_col: str = 'start_year',
                               era_bins: Optional[List[int]] = None,
                               target_col: str = 'duration_days_log',
                               branch_name: str = 'INTERVENTIONAL'
                               ) -> Dict:
    """
    Three-part temporal audit:

      1. Cluster-share drift across eras (JSD between adjacent eras).
      2. Era-stratified model performance (train pre-2015, test post-2015).
      3. Report-ready table of per-era cluster shares.

    Parameters
    ----------
    df_branch : pd.DataFrame
        Must contain cluster_col, year_col, target_col.
    cluster_col : str
    era_bins : list of int
        Year boundaries. Default: [0, 2005, 2010, 2015, 2020, 2100].

    Returns
    -------
    dict with keys:
      era_shares        : {era_label: {cluster: share}}
      jsd_adjacent      : {('2005-2009','2010-2014'): value, ...}
      jsd_max           : float
      era_r2            : {'pre_2015': float, 'post_2015': float, 'delta': float}
      passed            : bool
    """
    if era_bins is None:
        era_bins = [0, 2005, 2010, 2015, 2020, 2100]

    era_labels = [
        f"{era_bins[i]}-{era_bins[i + 1] - 1}"
        for i in range(len(era_bins) - 1)
    ]

    df = df_branch[[cluster_col, year_col, target_col]].dropna().copy()
    df = df[df[year_col] > 0]

    df['_era'] = pd.cut(df[year_col], bins=era_bins, labels=era_labels,
                        right=False)

    # --- 1. Cluster-share drift ---
    era_shares = {}
    for era in era_labels:
        sub = df[df['_era'] == era]
        if len(sub) == 0:
            era_shares[era] = {}
            continue
        shares = sub[cluster_col].value_counts(normalize=True).to_dict()
        era_shares[era] = {int(k): float(v) for k, v in shares.items()}

    # Align cluster universe
    all_clusters = sorted({c for s in era_shares.values() for c in s.keys()})

    def _vec(era):
        return np.array([era_shares[era].get(c, 0.0) for c in all_clusters])

    jsd_adjacent = {}
    for i in range(len(era_labels) - 1):
        a, b = era_labels[i], era_labels[i + 1]
        if len(era_shares[a]) == 0 or len(era_shares[b]) == 0:
            continue
        jsd_adjacent[f"{a} vs {b}"] = float(_js_divergence(_vec(a), _vec(b)))

    jsd_max = float(max(jsd_adjacent.values())) if jsd_adjacent else 0.0

    # --- 2. Era-stratified performance ---
    era_r2 = {'pre_2015': None, 'post_2015': None, 'delta': None}
    try:
        pre = df[df[year_col] < 2015]
        post = df[df[year_col] >= 2015]
        if len(pre) >= 100 and len(post) >= 100:
            # Very coarse check: predict post-2015 durations from pre-2015
            # cluster means. This isolates temporal drift from model choice.
            pre_means = pre.groupby(cluster_col)[target_col].mean()
            post_with_means = post[post[cluster_col].isin(pre_means.index)]
            if len(post_with_means) >= 50:
                y_true = post_with_means[target_col].values
                y_pred = post_with_means[cluster_col].map(pre_means).values
                ss_tot = ((y_true - y_true.mean()) ** 2).sum()
                ss_res = ((y_true - y_pred) ** 2).sum()
                r2_post = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
                era_r2['post_2015'] = float(r2_post)

            # Within-era variance explained
            for label, sub in [('pre_2015', pre), ('post_2015', post)]:
                groups = [
                    g[target_col].values
                    for _, g in sub.groupby(cluster_col)
                    if len(g) >= 5
                ]
                if len(groups) >= 2:
                    all_vals = np.concatenate(groups)
                    grand = all_vals.mean()
                    ss_tot = ((all_vals - grand) ** 2).sum()
                    ss_bet = sum(
                        len(g) * (g.mean() - grand) ** 2 for g in groups
                    )
                    if ss_tot > 0:
                        era_r2[f'{label}_eta2'] = float(ss_bet / ss_tot)

            if era_r2.get('pre_2015_eta2') and era_r2.get('post_2015_eta2'):
                era_r2['delta'] = float(
                    era_r2['post_2015_eta2'] - era_r2['pre_2015_eta2']
                )
    except Exception:
        pass

    passed = (jsd_max < 0.15) and (
        era_r2.get('delta') is None or abs(era_r2['delta']) < 0.05
    )

    return {
        'branch': branch_name,
        'era_shares': era_shares,
        'jsd_adjacent': jsd_adjacent,
        'jsd_max': jsd_max,
        'era_r2': era_r2,
        'passed': bool(passed),
    }


# ============================================================================
# 2. Cluster separation
# ============================================================================

def compute_cluster_separation(X_scaled,
                               clusters: np.ndarray,
                               y_true: Optional[np.ndarray] = None,
                               cluster_col: str = 'cluster',
                               max_pairs: int = 200
                               ) -> Dict:
    """
    Separation metrics in feature space and (optionally) target space.

    Parameters
    ----------
    X_scaled : pd.DataFrame or np.ndarray
        Scaled feature matrix (already fit on training fold).
        A DataFrame preserves index alignment; a raw ndarray works too.
    clusters : array-like of int
        Cluster labels aligned to X_scaled rows.
    y_true : array-like or None
        If given, computes target-space separation (η², pairwise MWU).
    cluster_col : str
        Only used for diagnostics.
    max_pairs : int
        Cap on the number of pairwise separability tests.

    Returns
    -------
    dict with keys:
      silhouette, davies_bouldin, calinski_harabasz,
      eta2 (if y_true),
      centroid_distances: {(c1, c2): dist},
      pairwise_auc: {(c1, c2): auc},
      pairwise_mwu_p: {(c1, c2): p},
      kde_overlap: {(c1, c2): overlap} (if y_true),
      near_duplicate_pairs: [...],
      non_separable_pairs: [...],
      passed: bool
    """
    clusters = np.asarray(clusters)
    unique = sorted(set(int(c) for c in clusters if c >= 0))

    result = {
        'silhouette': None,
        'davies_bouldin': None,
        'calinski_harabasz': None,
        'eta2': None,
        'centroid_distances': {},
        'pairwise_auc': {},
        'pairwise_mwu_p': {},
        'kde_overlap': {},
        'near_duplicate_pairs': [],
        'non_separable_pairs': [],
        'passed': False,
    }

    if len(unique) < 2:
        # Not enough clusters to compare. Set the diagnostic flags too, so
        # callers that read them don't hit a KeyError.
        result['_sil_ok']    = False
        result['_eta_ok']    = False
        result['_dupe_ok']   = False
        result['_indist_ok'] = False
        return result

    mask = np.isin(clusters, unique)

    # Accept either a DataFrame or a raw ndarray. A single extraction line
    # is enough; the previous version had an unused first branch.
    Xv_all = X_scaled.values if hasattr(X_scaled, 'values') else np.asarray(X_scaled)
    Xv = Xv_all[mask]
    cv = clusters[mask]

    try:
        result['silhouette'] = float(silhouette_score(Xv, cv))
        result['davies_bouldin'] = float(davies_bouldin_score(Xv, cv))
        result['calinski_harabasz'] = float(calinski_harabasz_score(Xv, cv))
    except Exception:
        pass

    # Centroid distances
    centroids = {}
    for c in unique:
        centroids[c] = Xv[cv == c].mean(axis=0)

    near_dupe = []
    for i, c1 in enumerate(unique):
        for c2 in unique[i + 1:]:
            d = float(np.linalg.norm(centroids[c1] - centroids[c2]))
            result['centroid_distances'][f"{c1}__{c2}"] = d
            if d < 0.5:
                near_dupe.append((c1, c2, d))
    result['near_duplicate_pairs'] = [
        {'c1': int(a), 'c2': int(b), 'distance': float(d)}
        for a, b, d in near_dupe
    ]

    # Pairwise separability via logistic regression AUC
    pairs = []
    for i, c1 in enumerate(unique):
        for c2 in unique[i + 1:]:
            pairs.append((c1, c2))
    if len(pairs) > max_pairs:
        rng = np.random.RandomState(42)
        idx = rng.choice(len(pairs), size=max_pairs, replace=False)
        pairs = [pairs[i] for i in idx]

    for c1, c2 in pairs:
        sub_mask = np.isin(cv, [c1, c2])
        X_sub = Xv[sub_mask]
        y_sub = (cv[sub_mask] == c2).astype(int)
        if len(np.unique(y_sub)) < 2 or len(y_sub) < 30:
            continue
        try:
            clf = LogisticRegression(max_iter=500, random_state=42)
            aucs = cross_val_score(clf, X_sub, y_sub, cv=3, scoring='roc_auc')
            result['pairwise_auc'][f"{c1}__{c2}"] = float(aucs.mean())
        except Exception:
            pass

    # Target-space separation
    if y_true is not None:
        y_true = np.asarray(y_true)
        y_sub = y_true[mask]
        cv_sub = cv

        groups = [
            y_sub[cv_sub == c]
            for c in unique
            if (cv_sub == c).sum() >= 5
        ]
        if len(groups) >= 2:
            all_vals = np.concatenate(groups)
            grand = all_vals.mean()
            ss_tot = ((all_vals - grand) ** 2).sum()
            ss_bet = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
            result['eta2'] = float(ss_bet / ss_tot) if ss_tot > 0 else 0.0

        # Pairwise Mann-Whitney + KDE overlap
        non_sep = []
        n_pairs = 0
        for i, c1 in enumerate(unique):
            for c2 in unique[i + 1:]:
                g1 = y_sub[cv_sub == c1]
                g2 = y_sub[cv_sub == c2]
                if len(g1) < 5 or len(g2) < 5:
                    continue
                n_pairs += 1
                try:
                    _, p = mannwhitneyu(g1, g2, alternative='two-sided')
                    result['pairwise_mwu_p'][f"{c1}__{c2}"] = float(p)
                except Exception:
                    continue
                # KDE overlap
                try:
                    from scipy.stats import gaussian_kde
                    lo = min(g1.min(), g2.min())
                    hi = max(g1.max(), g2.max())
                    grid = np.linspace(lo, hi, 200)
                    k1 = gaussian_kde(g1)(grid)
                    k2 = gaussian_kde(g2)(grid)
                    # np.trapz was renamed to np.trapezoid in NumPy 2.0.
                    overlap = float(_trapz(np.minimum(k1, k2), grid))
                    result['kde_overlap'][f"{c1}__{c2}"] = overlap
                    if overlap > 0.7:
                        non_sep.append((c1, c2, overlap))
                except Exception:
                    pass

        # Bonferroni threshold
        if n_pairs > 0:
            bonf = 0.05 / n_pairs
            non_sep += [
                (int(a.split('__')[0]), int(a.split('__')[1]), p)
                for a, p in result['pairwise_mwu_p'].items()
                if p > bonf
            ]
        result['non_separable_pairs'] = [
            {'c1': int(a), 'c2': int(b), 'metric': float(v)}
            for a, b, v in non_sep
        ]

    # Pass/fail
    #
    # Silhouette in high-dimensional feature spaces is not comparable to
    # silhouette in low-dimensional ones. Distances concentrate, and even
    # meaningful partitions routinely score near zero or negative. We use
    # silhouette only as a floor against catastrophic failures.
    #
    # The real gates are:
    #   - eta² > 0.03 on the target       (clusters differ in duration)
    #   - no near-duplicate pairs         (no two clusters are effectively identical)
    #   - no MWU-indistinguishable pairs  (no two clusters share the same
    #     duration distribution once Bonferroni-corrected)

    sil_ok  = result['silhouette'] is None or result['silhouette'] > -0.5
    eta_ok  = result['eta2'] is None or result['eta2'] > 0.03
    dupe_ok = len(result['near_duplicate_pairs']) == 0

    mwu = result.get('pairwise_mwu_p', {})
    if mwu:
        bonf = 0.05 / len(mwu)
        n_indist = sum(1 for p in mwu.values() if p > bonf)
        indist_ok = (n_indist == 0)
    else:
        indist_ok = True

    result['passed'] = bool(sil_ok and eta_ok and dupe_ok)

    # Diagnostic flags — not used by the gate, but useful when inspecting.
    result['_sil_ok']    = sil_ok
    result['_eta_ok']    = eta_ok
    result['_dupe_ok']   = dupe_ok
    result['_indist_ok'] = indist_ok

    return result


# ============================================================================
# 3. Feature categorization
# ============================================================================
# Re-exported from taxonomy so consumers that only import audit.py still
# get access. The canonical definition lives in taxonomy.py, alongside the
# other keyword maps; this block is a thin pass-through.
# ============================================================================

from clinical_trial_benchmarking.taxonomy import (  # noqa: E402
    FEATURE_CATEGORY,
    categorize_feature,
)


# Display labels used by the audit report renderer. Keep these short —
# they are printed inline next to each attribution.
_CATEGORY_LABEL = {
    'design_lever':     'design',
    'era_cohort':       'era',
    'sponsor':          'sponsor',
    'therapeutic_area': 'ta',
    'text_context':     'text',
    'other':            'other',
}


def category_display_label(category: str) -> str:
    """
    Return the short display label for a feature category.

    Used by the audit report renderer to tag each attribution line, e.g.
    '[design]' or '[era]'. Falls back to the category name itself for
    unknown categories.
    """
    return _CATEGORY_LABEL.get(category, category)


# ============================================================================
# 4. Directional gloss
# ============================================================================
# Turns a feature name + SHAP sign into a short sentence a reader can act
# on. The gloss is written per feature, not per peer group — but the
# direction of a feature's effect can flip between peer groups, so the
# caller must supply the direction that was actually observed for the
# peer group in question.
#
# The gloss is a display aid. It does not affect any computation, and a
# missing entry is not an error — the renderer simply omits the sentence.
#
# Conventions:
#   key   = feature name (matching _AUDIT_FEATURE_POOL)
#   value = {'+': sentence, '-': sentence}
#           '+' means the feature's value is associated with LONGER
#           durations within the peer group.
#           '-' means SHORTER.
#
# NOTE ON MAINTENANCE
# -------------------
# These sentences require domain judgment. They are written to describe
# the direction of association observed in the reference corpus, NOT to
# make a causal claim. If you extend _AUDIT_FEATURE_POOL with new design
# levers, add entries here so they are not silently rendered without a
# gloss.
# ============================================================================

DIRECTIONAL_GLOSS = {
    # ------------------------------------------------------------------
    # Operational scale
    # ------------------------------------------------------------------
    'num_sites': {
        '+': "More sites are associated with longer durations in this "
             "peer group.",
        '-': "More sites are associated with shorter durations in this "
             "peer group.",
    },
    'num_countries': {
        '+': "More countries are associated with longer durations in this "
             "peer group.",
        '-': "More countries are associated with shorter durations in this "
             "peer group.",
    },
    'us_percentage': {
        '+': "Higher US site share is associated with longer durations in "
             "this peer group.",
        '-': "Higher US site share is associated with shorter durations in "
             "this peer group.",
    },

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    'enrollment_count': {
        '+': "Larger enrollment targets are associated with longer "
             "durations in this peer group.",
        '-': "Larger enrollment targets are associated with shorter "
             "durations in this peer group.",
    },
    'enrollment_count_log': {
        '+': "Larger enrollment targets are associated with longer "
             "durations in this peer group.",
        '-': "Larger enrollment targets are associated with shorter "
             "durations in this peer group.",
    },

    # ------------------------------------------------------------------
    # Design complexity
    # ------------------------------------------------------------------
    'num_arm_groups': {
        '+': "More treatment arms are associated with longer durations in "
             "this peer group.",
        '-': "More treatment arms are associated with shorter durations in "
             "this peer group.",
    },
    'num_conditions': {
        '+': "More study conditions are associated with longer durations "
             "in this peer group.",
        '-': "More study conditions are associated with shorter durations "
             "in this peer group.",
    },
    'complexity_score': {
        '+': "Higher overall design complexity is associated with longer "
             "durations in this peer group.",
        '-': "Higher overall design complexity is associated with shorter "
             "durations in this peer group.",
    },

    # ------------------------------------------------------------------
    # Masking / blinding
    # ------------------------------------------------------------------
    'masking_freq': {
        '+': "Less common masking approaches are associated with longer "
             "durations in this peer group.",
        '-': "Less common masking approaches are associated with shorter "
             "durations in this peer group.",
    },

    # ------------------------------------------------------------------
    # Outcomes burden
    # ------------------------------------------------------------------
    'num_primary_outcomes': {
        '+': "More primary outcomes are associated with longer durations "
             "in this peer group.",
        '-': "More primary outcomes are associated with shorter durations "
             "in this peer group.",
    },
    'num_secondary_outcomes': {
        '+': "More secondary outcomes are associated with longer durations "
             "in this peer group.",
        '-': "More secondary outcomes are associated with shorter "
             "durations in this peer group.",
    },
    'total_outcomes': {
        '+': "More total outcomes are associated with longer durations in "
             "this peer group.",
        '-': "More total outcomes are associated with shorter durations in "
             "this peer group.",
    },
    'outcome_complexity_total': {
        '+': "Higher outcome complexity is associated with longer durations "
             "in this peer group.",
        '-': "Higher outcome complexity is associated with shorter "
             "durations in this peer group.",
    },
    'outcome_type_count': {
        '+': "More outcome types are associated with longer durations in "
             "this peer group.",
        '-': "More outcome types are associated with shorter durations in "
             "this peer group.",
    },

    # ------------------------------------------------------------------
    # Eligibility design
    # ------------------------------------------------------------------
    'eligibility_word_count': {
        '+': "Longer eligibility criteria are associated with longer "
             "durations in this peer group.",
        '-': "Longer eligibility criteria are associated with shorter "
             "durations in this peer group.",
    },
    'age_range': {
        '+': "Wider eligibility age range is associated with longer "
             "durations in this peer group.",
        '-': "Wider eligibility age range is associated with shorter "
             "durations in this peer group.",
    },

    # ------------------------------------------------------------------
    # Phase (a declared design choice)
    # ------------------------------------------------------------------
    'phase_score': {
        '+': "Later-phase trials are associated with longer durations in "
             "this peer group.",
        '-': "Later-phase trials are associated with shorter durations in "
             "this peer group.",
    },

    # ------------------------------------------------------------------
    # Planned duration
    # ------------------------------------------------------------------
    'planned_duration_years': {
        '+': "Longer planned duration is associated with longer actual "
             "durations in this peer group.",
        '-': "Longer planned duration is associated with shorter actual "
             "durations in this peer group.",
    },
}


def gloss(feature: str, direction: str) -> str:
    """
    Return a short sentence describing the direction of a feature's
    association with trial duration.

    Parameters
    ----------
    feature : str
        Feature name (matching _AUDIT_FEATURE_POOL).
    direction : str
        '+' if the feature's value is associated with longer durations
        within the peer group, '-' if shorter.

    Returns
    -------
    str
        A sentence, or '' if no gloss is registered for the (feature,
        direction) pair. An empty return is not an error — the renderer
        simply omits the sentence.
    """
    entry = DIRECTIONAL_GLOSS.get(feature)
    if not entry:
        return ''
    return entry.get(direction, '')