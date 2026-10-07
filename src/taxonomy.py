"""
Canonical keyword maps and display dictionaries used by both the
segmentation notebook (02) and the forecasting notebook (03).

Single source of truth so the two notebooks cannot drift apart.
"""

# ---------------------------------------------------------------------------
# Therapeutic-area keyword sets.
#
# Every TA listed here produces a flag column f'is_{name}' in notebook 02's
# Cell 3.2, and participates in the single-label therapeutic_area assignment
# in Cell 9.1. The ORDER of THERAPEUTIC_AREA_COLUMNS below determines which
# TA wins when a trial's conditions text fires multiple flags — see the
# comment on that list.
# ---------------------------------------------------------------------------
THERAPEUTIC_AREA_EXTENDED = {
    'oncology': [
        'cancer', 'tumor', 'malignant', 'carcinoma', 'sarcoma', 'lymphoma',
        'leukemia', 'melanoma', 'neoplasm', 'metastatic', 'breast cancer',
        'lung cancer', 'prostate cancer', 'colorectal cancer', 'ovarian cancer',
        'pancreatic cancer', 'hepatocellular', 'glioblastoma', 'myeloma',
    ],
    'cardiovascular': [
        'heart', 'cardiac', 'cardiovascular', 'myocardial', 'infarction',
        'stroke', 'hypertension', 'atrial fibrillation', 'heart failure',
        'coronary', 'angina', 'arrhythmia', 'thrombosis', 'embolism',
        'pulmonary hypertension', 'aortic', 'valve', 'cerebrovascular',
    ],
    'neurology': [
        'neurological', 'neurology', 'brain', 'spinal', 'cerebral',
        'parkinson', 'alzheimer', 'dementia', 'multiple sclerosis',
        'epilepsy', 'seizure', 'migraine', 'neuropathy', 'stroke',
        'headache', 'tremor', 'ataxia', 'amyotrophic', 'als', 'huntington',
    ],
    'infectious_disease': [
        'infection', 'infectious', 'viral', 'bacterial', 'fungal',
        'hiv', 'aids', 'hepatitis', 'influenza', 'pneumonia',
        'tuberculosis', 'malaria', 'covid', 'coronavirus', 'sepsis',
        'meningitis', 'encephalitis', 'abscess', 'cellulitis',
    ],
    'endocrine': [
        'diabetes', 'diabetic', 'endocrine', 'thyroid', 'hyperthyroidism',
        'hypothyroidism', 'metabolic', 'obesity', 'overweight', 'glucose',
        'insulin', 'glycemic', 'adrenal', 'pituitary', 'cushing', 'addison',
    ],
    'autoimmune': [
        'autoimmune', 'rheumatoid', 'arthritis', 'lupus', 'scleroderma',
        'sjogren', 'psoriasis', 'crohn', 'colitis', 'ulcerative',
        'multiple sclerosis', 'autoimmune hepatitis', 'vasculitis',
    ],
    'respiratory': [
        'asthma', 'copd', 'respiratory', 'pulmonary', 'lung', 'emphysema',
        'bronchitis', 'cystic fibrosis', 'apnea', 'pneumonia', 'pleural',
    ],
    'gastrointestinal': [
        'gastrointestinal', 'digestive', 'colon', 'stomach', 'bowel',
        'ibs', 'gastric', 'ulcer', 'reflux', 'hepatitis', 'cirrhosis',
        'pancreatitis', 'gallbladder', 'esophagus', 'intestinal',
    ],
    'psychiatry': [
        'depression', 'anxiety', 'bipolar', 'schizophrenia', 'psychiatric',
        'mental', 'psychosis', 'mood', 'ptsd', 'ocd', 'panic',
        'eating disorder', 'addiction', 'substance abuse', 'alcoholism',
    ],
    'musculoskeletal': [
        'orthopedic', 'musculoskeletal', 'bone', 'joint', 'fracture',
        'osteoporosis', 'back pain', 'spine', 'skeletal', 'muscular',
        'dystrophy', 'myopathy', 'tendon', 'ligament', 'arthritis',
    ],
    'dermatology': [
        'dermatology', 'skin', 'dermatitis', 'eczema', 'psoriasis',
        'acne', 'melanoma', 'wound', 'ulcer', 'burn', 'scar',
    ],
    'ophthalmology': [
        'ophthalmology', 'eye', 'vision', 'retina', 'glaucoma',
        'cataract', 'macular', 'cornea', 'conjunctivitis', 'uveitis',
    ],
    'renal': [
        'renal', 'kidney', 'nephrology', 'dialysis', 'glomerular',
        'proteinuria', 'creatinine', 'urinary', 'bladder', 'renal failure',
    ],
    'hematology': [
        'hematology', 'blood', 'anemia', 'thrombocytopenia', 'coagulation',
        'hemophilia', 'sickle cell', 'thalassemia', 'leukemia', 'lymphoma',
    ],
    'pediatrics': [
        'pediatric', 'infant', 'neonatal', 'children', 'adolescent',
        'childhood', 'newborn', 'premature', 'development',
    ],
    'geriatrics': [
        'geriatric', 'elderly', 'aging', 'senior', 'older adult',
    ],
    'women_health': [
        'pregnancy', 'pregnant', 'maternal', 'obstetric', 'gynecologic',
        'menopause', 'menstrual', 'ovarian', 'uterine', 'cervical',
        'endometriosis', 'fibroid', 'breast',
    ],
    'rare_disease': [
        'rare disease', 'orphan', 'ultra-rare', 'rare disorder',
    ],
}

# DEPRECATED ALIAS. Kept so existing code that imports
# THERAPEUTIC_AREA_KEYWORDS picks up the extended taxonomy without change.
# New code should import THERAPEUTIC_AREA_EXTENDED directly.
THERAPEUTIC_AREA_KEYWORDS = THERAPEUTIC_AREA_EXTENDED

# ---------------------------------------------------------------------------
# Flag-column names and priority order.
#
# The list below is the *priority order* for single-label assignment in
# Cell 9.1: np.select returns the FIRST matching flag, so a TA earlier in
# this list wins ties against a TA later in the list. Overlaps between
# keyword sets are common (e.g. 'psoriasis' fires both autoimmune and
# dermatology; 'leukemia' fires both oncology and hematology), so this
# ordering is a deliberate design choice, not an incidental file order.
#
# Rule of thumb: most specific / most clinically distinct first. A trial
# tagged 'rare disease' should be labelled rare_disease, not whatever
# broader TA its condition text happens to also match.
# ---------------------------------------------------------------------------
THERAPEUTIC_AREA_COLUMNS = [
    'is_rare_disease',
    'is_oncology',
    'is_hematology',
    'is_autoimmune',
    'is_neurology',
    'is_cardiovascular',
    'is_infectious_disease',
    'is_respiratory',
    'is_endocrine',
    'is_gastrointestinal',
    'is_renal',
    'is_dermatology',
    'is_musculoskeletal',
    'is_ophthalmology',
    'is_psychiatry',
    'is_pediatrics',
    'is_geriatrics',
    'is_women_health',
]

TA_STRING_TO_FLAG = {c.replace('is_', ''): c for c in THERAPEUTIC_AREA_COLUMNS}

CONDITION_KEYWORDS = {
    'has_breast_cancer':     ['breast cancer', 'breast carcinoma', 'breast neoplasm'],
    'has_lung_cancer':       ['lung cancer', 'nsclc', 'sclc', 'pulmonary neoplasm'],
    'has_colorectal_cancer': ['colorectal', 'colon cancer', 'rectal cancer'],
    'has_prostate_cancer':   ['prostate cancer', 'prostate carcinoma'],
    'has_leukemia':          ['leukemia', 'leukaemia', 'aml', 'cml', 'all', 'cll'],
    'has_lymphoma':          ['lymphoma', 'hodgkin', 'non-hodgkin'],
    'has_melanoma':          ['melanoma'],
    'has_diabetes_t1':       ['type 1 diabetes', 't1dm', 'insulin-dependent'],
    'has_diabetes_t2':       ['type 2 diabetes', 't2dm', 'non-insulin-dependent'],
    'has_obesity':           ['obesity', 'overweight', 'bmi'],
    'has_alzheimer':         ['alzheimer'],
    'has_parkinson':         ['parkinson'],
    'has_depression':        ['depression', 'depressive'],
    'has_anxiety':           ['anxiety', 'anxious'],
    'has_hiv':               ['hiv', 'human immunodeficiency'],
    'has_hepatitis':         ['hepatitis'],
    'has_covid':             ['covid', 'sars-cov-2', 'coronavirus'],
    'has_asthma':            ['asthma'],
    'has_copd':              ['copd', 'chronic obstructive'],
    'has_rare_disease':      ['rare disease', 'orphan disease', 'ultra-rare'],
}

KEYWORD_FLAGS = {
    'kw_randomized':     ['randomized', 'randomised', 'randomization'],
    'kw_double_blind':   ['double-blind', 'double blind'],
    'kw_placebo':        ['placebo'],
    'kw_longitudinal':   ['longitudinal', 'follow-up', 'follow up'],
    'kw_extension':      ['extension study', 'extension phase'],
    'kw_biomarker':      ['biomarker'],
    'kw_adaptive':       ['adaptive design', 'adaptive trial'],
    'kw_phase3':         ['phase 3', 'phase iii'],
    'kw_phase2':         ['phase 2', 'phase ii'],
    'kw_phase1':         ['phase 1', 'phase i'],
}

OUTCOME_TEXT_KEYWORDS = {
    'outcome_has_overall_survival': ['overall survival', ' os ', 'os)', '(os'],
    'outcome_has_pfs':              ['progression-free survival', 'progression free survival', 'pfs'],
    'outcome_has_orr':              ['overall response rate', 'objective response rate', 'orr'],
    'outcome_has_dfs':              ['disease-free survival', 'disease free survival', 'dfs'],
    'outcome_has_ae':               ['adverse event', 'adverse events', 'safety'],
    'outcome_has_qol':              ['quality of life', 'qol', 'sf-36', 'eq-5d'],
    'outcome_has_biomarker':        ['biomarker', 'biomarkers'],
    'outcome_has_pk':               ['pharmacokinetic', 'auc', 'cmax', 'clearance'],
    'outcome_has_immunogenicity':   ['immunogenicity', 'antibody', 'anti-drug'],
    'outcome_has_mortality':        ['mortality', 'death'],
    'outcome_has_hospitalization':  ['hospitalization', 'hospitalisation'],
    'outcome_has_time_to_event':    ['time to event', 'time-to-event'],
}

TA_DISPLAY = {
    'oncology':           'Oncology',
    'cardiovascular':     'Cardiovascular',
    'neurology':          'Neurology',
    'infectious_disease': 'Infectious Disease',
    'endocrine':          'Endocrine',
    'autoimmune':         'Autoimmune',
    'respiratory':        'Respiratory',
    'gastrointestinal':   'Gastrointestinal',
    'psychiatry':         'Psychiatry',
    'musculoskeletal':    'Musculoskeletal',
    'dermatology':        'Dermatology',
    'ophthalmology':      'Ophthalmology',
    'renal':              'Renal',
    'hematology':         'Hematology',
    'pediatrics':         'Pediatrics',
    'geriatrics':         'Geriatrics',
    'women_health':       "Women's Health",
    'rare_disease':       'Rare Disease',
    'other':              'Other',
}

SPONSOR_DISPLAY = {
    'industry':    'Industry',
    'academic':    'Academic',
    'government':  'Government',
    'network':     'Network',
    'other':       'Other',
    'unknown':     'Unknown Sponsor',
}

FEATURE_FAMILIES = {
    'enrollment': [
        'enrollment_count', 'enrollment_count_log', 'log_enrollment',
        'protocolSection.designModule.enrollmentInfo.count',
    ],
    'complexity': [
        'complexity_score', 'complexity_score_log', 'operational_complexity_score',
    ],
    'outcome_counts': [
        'total_outcomes', 'outcome_complexity_total', 'outcome_type_count',
        'outcome_type_diversity', 'reporting_burden_score',
        'num_primary_outcomes', 'num_secondary_outcomes',
    ],
    'phase': [
        'phase_score', 'phase_progression_score', 'phase_coverage',
        'has_phase0', 'has_phase1', 'has_phase2', 'has_phase3', 'has_phase4',
    ],
    'eligibility': [
        'eligibility_word_count', 'eligibility_word_count_log',
    ],
}

# ---------------------------------------------------------------------------
# Observational-study axes for the branch-specific Strategy A partition.
#
# Interventional trials have phases; observational studies do not. CT.gov
# encodes observational design via two fields instead:
#   observationalModel — Cohort, Case-Control, Case-Only, Case-Crossover,
#                        EcologicOrCommunity, FamilyBased, Other
#   timePerspective    — Prospective, Retrospective, Cross-Sectional, Other
#
# These two axes are the observational analogue of "stage × scope". They
# are registration-time, ordinal-ish, and interpretable — a reviewer can
# name every cell ("prospective cohort", "retrospective case-control").
# ---------------------------------------------------------------------------
OBSERVATIONAL_MODEL_VALUES = [
    'cohort',
    'case-control',
    'case-only',
    'case-crossover',
    'ecologic',
    'family-based',
    'other',
]

OBSERVATIONAL_PERSPECTIVE_VALUES = [
    'prospective',
    'retrospective',
    'cross-sectional',
    'other',
]

# Map the raw CT.gov enum (which is CamelCase) to the lowercase canonical
# values above. Anything not in the map falls through to 'other'.
OBSERVATIONAL_MODEL_MAP = {
    'COHORT':              'cohort',
    'CASE_CONTROL':        'case-control',
    'CASE_CONTROLS':       'case-control',
    'CASE_ONLY':           'case-only',
    'CASE_CROSSOVER':      'case-crossover',
    'ECOLOGIC_OR_COMMUNITY': 'ecologic',
    'FAMILY_BASED':        'family-based',
    'OTHER':               'other',
}

OBSERVATIONAL_PERSPECTIVE_MAP = {
    'PROSPECTIVE':    'prospective',
    'RETROSPECTIVE':  'retrospective',
    'CROSS_SECTIONAL': 'cross-sectional',
    'CROSS-SECTIONAL': 'cross-sectional',
    'OTHER':          'other',
}

# ===========================================================================
# FEATURE CATEGORIZATION
# ===========================================================================
# Assigns every audit feature to one of five categories, so downstream
# consumers can distinguish features a sponsor can control at design time
# (design_lever) from features that describe the trial but cannot be
# changed (context).
#
# The categories are:
#
#   design_lever     — a design choice set by the sponsor. Actionable in
#                      the sense that the value is under the sponsor's
#                      control at protocol design time. Examples: number
#                      of sites, enrollment target, masking, outcome count.
#
#   era_cohort       — describes WHEN the trial was run. Not controllable.
#                      Present in the model because operational norms drift
#                      over time, but not a design lever. Examples:
#                      years_since_registration.
#
#   sponsor          — describes WHO ran the trial. Not controllable as a
#                      design choice (a sponsor is what it is). Examples:
#                      funding_industry, is_public_funded.
#
#   therapeutic_area — describes WHAT the trial studies. Not a design
#                      choice. Examples: is_oncology, is_neurology.
#
#   text_context     — text-derived features that do not map cleanly to a
#                      single category. Some are weak levers (eligibility
#                      word count is somewhat controllable), some are
#                      proxies for trial complexity. Reported separately
#                      so the reader can judge them individually.
#
#   other            — everything else. Fallback so categorize_feature()
#                      never raises. Should stay small.
#
# IMPORTANT: membership is best-effort. A feature's category is a display
# aid, not a partition key. The audit report uses it to sort and label
# attributions; it does not gate any computation. If a feature is
# miscategorized, the worst outcome is that it appears in the wrong
# section of a printed report.
# ===========================================================================

FEATURE_CATEGORY = {
    # ------------------------------------------------------------------
    # DESIGN LEVERS
    # Values the sponsor sets during protocol design.
    # ------------------------------------------------------------------
    'design_lever': {
        # Operational scale
        'num_sites', 'num_countries', 'us_sites', 'us_percentage',
        'has_locations',

        # Enrollment
        'enrollment_count', 'enrollment_count_log', 'log_enrollment',

        # Design complexity
        'num_arm_groups', 'num_conditions',
        'complexity_score', 'complexity_score_log',

        # Masking / blinding
        'masking_freq',

        # Outcomes burden
        'num_primary_outcomes', 'num_secondary_outcomes', 'num_other_outcomes',
        'total_outcomes', 'outcome_complexity_total',
        'outcome_complexity_primary', 'outcome_complexity_secondary',
        'outcome_type_count', 'outcome_type_diversity', 'outcome_balance',
        'has_efficacy_outcome', 'has_safety_outcome',
        'has_quality_of_life_outcome', 'has_survival_outcome',
        'has_biomarker_outcome', 'has_pharmacokinetic_outcome',
        'has_pharmacodynamic_outcome', 'has_patient_reported_outcome',

        # Phase (a design choice — the sponsor declares the phase)
        'phase_score', 'phase_count', 'phase_coverage',
        'phase_progression_score', 'phase_consecutive', 'phase_gaps',
        'is_early_phase', 'is_late_phase', 'is_mixed_phase',
        'has_phase0', 'has_phase1', 'has_phase2', 'has_phase3', 'has_phase4',
        'phase_combo_1', 'phase_combo_2', 'phase_combo_3', 'phase_combo_4',
        'phase_combo_1-2', 'phase_combo_1-2-3', 'phase_combo_1-2-3-4',
        'phase_combo_2-3', 'phase_combo_2-3-4', 'phase_combo_3-4',

        # Eligibility design
        'eligibility_word_count', 'eligibility_word_count_log',
        'min_age', 'max_age', 'age_range',

        # Planned duration (target set by sponsor)
        'planned_duration_years', 'planned_duration_days',
    },

    # ------------------------------------------------------------------
    # ERA / COHORT
    # Describes when the trial ran. Not controllable.
    # ------------------------------------------------------------------
    'era_cohort': {
        'years_since_registration',
        'years_since_registration_log',
        'start_year',  # forbidden from the pool but included for safety
    },

    # ------------------------------------------------------------------
    # SPONSOR
    # Describes who ran the trial. Not a design choice.
    # ------------------------------------------------------------------
    'sponsor': {
        'funding_industry', 'funding_government', 'funding_academic',
        'funding_nonprofit', 'funding_international', 'funding_other',
        'funding_unknown',
        'funding_source_count', 'funding_diversity',
        'is_industry_funded', 'is_public_funded', 'is_nonprofit_funded',
        'funding_industry_academic', 'funding_gov_academic',
        'funding_industry_gov',
        'primary_funding',
        'sponsor_type_regime',
        'protocolSection.sponsorCollaboratorsModule.leadSponsor.class_freq',
    },

    # ------------------------------------------------------------------
    # THERAPEUTIC AREA
    # Describes what the trial studies. Not a design choice.
    # ------------------------------------------------------------------
    'therapeutic_area': {
        f'is_{name}' for name in [
            'oncology', 'cardiovascular', 'neurology',
            'infectious_disease', 'endocrine', 'autoimmune',
            'respiratory', 'gastrointestinal', 'psychiatry',
            'musculoskeletal', 'dermatology', 'ophthalmology',
            'renal', 'hematology', 'pediatrics', 'geriatrics',
            'women_health', 'rare_disease',
        ]
    },

    # ------------------------------------------------------------------
    # TEXT CONTEXT
    # Text-derived features that do not map cleanly to design_lever.
    # Some are weak levers; some are complexity proxies. Reported
    # separately so the reader can judge them.
    # ------------------------------------------------------------------
    'text_context': {
        'elig_text_len', 'elig_text_sentence_count',
        'elig_text_numeric_token_count',
        'elig_text_prior_therapy_mention', 'elig_text_placebo_mention',
        'elig_text_age_bound_present',
    },
}


def categorize_feature(name: str) -> str:
    """
    Return the category of an audit feature.

    The result is one of:
        'design_lever', 'era_cohort', 'sponsor',
        'therapeutic_area', 'text_context', 'other'

    Never raises. Unknown features fall through to 'other'.

    This is a display aid, not a partition key. The audit report uses it
    to sort and label attributions. It does not gate any computation.
    """
    for category, members in FEATURE_CATEGORY.items():
        if name in members:
            return category
    return 'other'