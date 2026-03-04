# ──────────────────────────────────────────────────────────
# MER Page Classification Config
#
# Edit keywords and thresholds here.
# No need to touch page_classifier.py logic.
# ──────────────────────────────────────────────────────────

# Minimum rapidfuzz partial_ratio score (0-100) to count a keyword as matched.
FUZZY_THRESHOLD = 80

# Minimum fraction of keywords matched (0.0-1.0) to auto-accept a page mapping.
# Pages below this are flagged in "needs_review".
CONFIDENCE_THRESHOLD = 0.7

# Keywords that identify each MER page.
# Key = MER page number (int), Value = list of expected text fragments.
PAGE_IDENTIFIERS = {
    1: [
        "SBI Life Insurance Co. Ltd",
        "Medical Examination Report",
        "Branch Name",
        "Proposal Number",
        "Full Name of Life Assured",
        "Form of Identification Produced",
        "PART I",
        "Questions to be put up by the Medical Examiner",
        "Name & Address of your personal physician",
        "Diabetes or raised blood sugar",
        "Hypertension or blood pressure",
        "Heart attack, chest pain, bypass",
        "Cancer or leukaemia",
        "Hormonal or glandular disorders",
        "disorder of the eye, ear or nose",
        "digestive system, ulcer, colitis",
        "respiratory problem including asthma",
        "Aadhaar",
        "Driving License",
        "Ration Card",
    ],
    2: [
        ":: 2 ::",
        "Kidney disorder, renal stones",
        "Chronic ulceration on skin",
        "blood thinners, Oral steroids",
        "Immunosuppressant",
        "Insomnia, depression, stress-related",
        "nervous breakdown, epilepsy, fits",
        "permanent disability",
        "radiological/cardiological/pathological",
        "USG/CT Scan/MRI",
        "CT angiography, Angiogram",
        "endoscopy, biopsy, FNAC",
        "hospitalization/operation/surgery",
        "organ transplant",
        "physical deformity/congenital disease",
        "vision and hearing normal",
        "accident or suffer any injury",
        "sexually transmitted disease",
        "consume alcohol",
        "Type of Alcohol",
    ],
    3: [
        ":: 3 ::",
        "smoker or have you ever smoked tobacco",
        "Cigarettes / Bidis / Roll-ups",
        "Chewing tobacco / Paan Masala",
        "sticks/day",
        "pouches/day",
        "For Females",
        "disease of breast or genital organs",
        "mammogram",
        "ultrasound of the pelvis",
        "gynaecological investigations",
        "complications during pregnancy",
        "gestational diabetes",
        "Are you now pregnant",
        "Family History of Life Assured",
        "Alive/Not Alive",
        "Present Age/Age at Death",
        "cause of death",
        "Declaration by Life Assured",
        "Signature of Parents",
    ],
    4: [
        "physical measurement",
        "pulse / minute",
        "type of irregularity",
        "systemic examination",
        "medically fit on examination",
        "certificate",
        "registration",
        "cardiovascular system",
        "respiratory system",
        "digestive system",
        "nervous system",
        "genito-urinary system",
        "musculoskeletal system",
        "blood disorders",
        "evidence of operation",
        "evidence of injury",
        "name of doctor",
        "signature of doctor",
        "qualification",
        "degree of impairment",
    ],
}

# Keywords for Page 5 (Insurance Requirements page)
# This page is optional and contains test requirements
PAGE_5_IDENTIFIERS = [
    "Ins Test Remark",
    "HI Test Remark",
    "Life to be Assured",
    "FRS Details",
    "Confidence",
    "Similarity",
    "Proposal No",
]
