"""Procedure registry.

Adding a surgical procedure means adding one entry to PROCEDURES: the intake
chips, intra-operative options, post-operative reference protocol and symptom
keywords are all data. No frontend or agent code needs to change
(NFR: Scalability / Maintainability).

Reference protocols summarise the verification checklists (WSES, SAGES, ACS,
ATA and similar). They ground the AI output and are shown on their own when
the AI service is unavailable. They support, and never replace, clinician
judgement.
"""

COMMON_INTAKE = {
    "sex": ["Male", "Female", "Other"],
    "urgency": ["Emergency", "Urgent", "Elective"],
    "asa": ["ASA I", "ASA II", "ASA III", "ASA IV"],
    "smoking": ["Never", "Former", "Current"],
    "alcohol": ["None", "Occasional", "Heavy"],
    "prior_surgery": ["None", "Previous abdominal surgery", "Previous surgery at this site"],
    "comorbidities": [
        "Diabetes", "Hypertension", "Heart disease", "Asthma / COPD",
        "Kidney disease", "Liver disease", "Obesity", "Thyroid disease",
        "Bleeding disorder", "Immunosuppressed", "Pregnancy",
    ],
    "allergies": [
        "Penicillin", "Cephalosporins", "Sulfa drugs", "NSAIDs",
        "Latex", "Iodine / contrast", "Opioids",
    ],
    "medications": [
        "Anticoagulant", "Antiplatelet (aspirin / clopidogrel)", "Insulin",
        "Metformin", "Antihypertensives", "Steroids", "NSAIDs",
        "Levothyroxine", "Antithyroid drugs",
    ],
}

COMMON_INTRAOP = {
    "approach": ["Laparoscopic", "Open", "Robotic", "Converted to open"],
    "findings": [
        "As expected", "Perforation", "Abscess / pus", "Gross contamination",
        "Adhesions", "Malignancy suspected", "Difficult anatomy",
    ],
    "events": [
        "Bleeding > expected", "Organ / structure injury", "Anesthesia event",
        "Hemodynamic instability", "None",
    ],
    "blood_loss": ["Minimal (<50 ml)", "Moderate (50-250 ml)", "Significant (>250 ml)"],
    "drain": ["No drain", "Drain placed"],
    "specimen": ["Sent for histopathology", "Not sent"],
}

PROCEDURES = [
    {
        "id": "appendectomy",
        "name": "Appendectomy",
        "category": "Emergency general surgery",
        "keywords": ["right lower quadrant", "rlq", "appendicitis", "fever", "anorexia", "nausea", "migratory pain"],
        "symptoms": [
            "Right lower abdominal pain", "Migratory periumbilical pain", "Nausea / vomiting",
            "Fever", "Loss of appetite", "Rebound tenderness", "Raised WBC / CRP",
        ],
        "intraop_extras": {
            "stump_closure": ["Endoloop", "Stapler", "Suture ligation"],
            "irrigation": ["No irrigation", "Irrigation done"],
        },
        "protocol": {
            "recovery_time": "1-3 weeks for laparoscopic; longer if open or perforated.",
            "medications": [
                "Multimodal analgesia: paracetamol plus NSAID if no contraindication; short-course opioid only for breakthrough pain.",
                "Uncomplicated appendicitis: no routine post-operative antibiotics (WSES).",
                "Perforated / complicated: continue broad-spectrum IV antibiotics, generally 3-5 days or until fever, WBC and CRP settle.",
                "Antiemetic as required; VTE prophylaxis per risk.",
            ],
            "wound_care": [
                "Keep incisions clean and dry; inspect daily for redness, swelling or discharge.",
                "Remove any drain before discharge if output is minimal.",
            ],
            "diet_activity": [
                "Clear liquids, then advance diet as tolerated.",
                "Early ambulation to prevent ileus and VTE.",
            ],
            "discharge_criteria": [
                "Afebrile, tolerating oral diet, pain controlled on oral medication, passing flatus.",
                "Uncomplicated laparoscopic cases are often discharged same day or next day.",
            ],
            "follow_up": ["Clinic review at 1-4 weeks; review histopathology result."],
            "red_flags": [
                "Fever above 38.3 C (101 F)", "Worsening abdominal pain or distension",
                "Persistent vomiting", "Wound redness, pus or opening",
                "Pelvic or abdominal abscess signs",
            ],
        },
    },
    {
        "id": "lap-cholecystectomy",
        "name": "Laparoscopic cholecystectomy",
        "category": "Hepatobiliary",
        "keywords": ["right upper quadrant", "ruq", "gallstones", "biliary colic", "fatty meal", "jaundice", "cholecystitis"],
        "symptoms": [
            "Right upper quadrant pain", "Pain after fatty meals", "Nausea / vomiting",
            "Fever", "Jaundice", "Gallstones on ultrasound", "Murphy sign positive",
        ],
        "intraop_extras": {
            "critical_view_of_safety": ["Achieved", "Not achieved"],
            "bile_leak_check": ["No leak", "Leak noted"],
        },
        "protocol": {
            "recovery_time": "1-2 weeks after laparoscopy; 4-6 weeks after open surgery.",
            "medications": [
                "Paracetamol and NSAID (if no contraindication); opioids only for breakthrough pain.",
                "Post-operative antibiotics not routinely needed for uncomplicated cases; consider if gangrenous or perforated gallbladder or cholangitis.",
                "Antiemetic as required; VTE prophylaxis per risk.",
            ],
            "wound_care": [
                "Keep port sites clean and dry; shower allowed, avoid soaking.",
                "Monitor any drain output for bile.",
            ],
            "diet_activity": [
                "Clear liquids then advance as tolerated; a lower-fat diet may ease transient diarrhea or bloating.",
                "Walk early; avoid heavy lifting for about 1-2 weeks (4-6 weeks after open).",
            ],
            "discharge_criteria": [
                "Pain controlled orally, tolerating diet, afebrile, no jaundice. Often same day (laparoscopic) or 1-3 days (open).",
            ],
            "follow_up": ["Review at 1-2 weeks; check histopathology and LFTs if symptoms."],
            "red_flags": [
                "Jaundice or dark urine", "Fever or rigors", "Severe or increasing abdominal pain",
                "Bilious drain output or abdominal distension (bile leak / bile duct injury)",
                "Persistent vomiting", "Wound infection",
            ],
        },
    },
    {
        "id": "inguinal-hernia-repair",
        "name": "Inguinal hernia repair",
        "category": "Abdominal wall",
        "keywords": ["groin", "bulge", "inguinal", "hernia", "scrotal swelling", "straining"],
        "symptoms": [
            "Groin bulge", "Groin pain on straining", "Scrotal swelling",
            "Irreducible lump", "Nausea / vomiting with pain", "Previous hernia repair",
        ],
        "intraop_extras": {
            "technique": ["Open mesh (Lichtenstein)", "Laparoscopic TEP", "Laparoscopic TAPP", "Tissue repair"],
            "mesh": ["Mesh used", "No mesh"],
        },
        "protocol": {
            "recovery_time": "Full recovery in about 4-6 weeks.",
            "medications": [
                "Paracetamol and NSAID (if no contraindication); ice and scrotal support.",
                "No routine post-operative antibiotics for clean elective repair.",
            ],
            "wound_care": [
                "Keep wound clean and dry; watch for scrotal hematoma or seroma.",
            ],
            "diet_activity": [
                "Normal diet as tolerated; avoid constipation and straining.",
                "Walk within hours; avoid heavy lifting and strenuous activity for 2-4 weeks.",
            ],
            "discharge_criteria": [
                "Voiding, pain controlled orally, mobilizing; usually same day or next morning.",
            ],
            "follow_up": ["Review at 2-4 weeks for wound and recurrence check."],
            "red_flags": [
                "Urinary retention", "Rapidly enlarging scrotal swelling or bruising",
                "Fever or wound discharge (possible mesh infection)",
                "Severe or persistent groin pain / numbness (nerve entrapment)",
                "Bulge recurrence",
            ],
        },
    },
    {
        "id": "colectomy",
        "name": "Colectomy (colon resection)",
        "category": "Colorectal",
        "keywords": ["colon", "bowel", "diverticulitis", "colorectal", "cancer", "obstruction", "rectal bleeding", "change in bowel habit", "ibd"],
        "symptoms": [
            "Change in bowel habit", "Rectal bleeding", "Left lower abdominal pain",
            "Weight loss", "Bowel obstruction", "Known colon cancer", "Diverticulitis / IBD",
        ],
        "intraop_extras": {
            "anastomosis": ["Primary anastomosis", "Colostomy", "Ileostomy", "Hartmann procedure"],
            "perfusion_check": ["Bowel perfusion adequate", "Perfusion concern"],
        },
        "protocol": {
            "recovery_time": "Hospital stay 3-7 days; full recovery about 4-6 weeks.",
            "medications": [
                "Multimodal opioid-sparing analgesia (paracetamol, NSAID if renal function allows).",
                "Antibiotics only as per contamination (complicated or perforated disease); do not extend routine prophylaxis beyond 24 hours.",
                "VTE prophylaxis (pharmacological plus mechanical); antiemetic; early removal of urinary catheter.",
            ],
            "wound_care": [
                "Wound checks for infection; stoma care teaching and stoma viability check if formed.",
            ],
            "diet_activity": [
                "Enhanced recovery: early oral intake once bowel function returns, advance to low-fibre diet.",
                "Early ambulation and incentive spirometry to prevent DVT and atelectasis.",
            ],
            "discharge_criteria": [
                "Passing flatus or stool, tolerating diet, pain controlled orally, afebrile, safe stoma function if present.",
            ],
            "follow_up": ["Wound check and pathology review at 2 weeks; oncology referral if malignant."],
            "red_flags": [
                "Fever, tachycardia or worsening abdominal pain (anastomotic leak)",
                "Peritonitis or abdominal distension", "Persistent vomiting or ileus",
                "Bleeding or dusky / retracted stoma", "Wound infection or abscess",
            ],
        },
    },
    {
        "id": "thyroidectomy",
        "name": "Thyroidectomy",
        "category": "Endocrine",
        "keywords": ["thyroid", "neck", "goiter", "nodule", "hyperthyroid", "graves", "voice", "swallowing"],
        "symptoms": [
            "Neck swelling / goiter", "Thyroid nodule", "Hyperthyroid symptoms",
            "Difficulty swallowing", "Voice change", "Confirmed thyroid cancer",
        ],
        "intraop_extras": {
            "extent": ["Total thyroidectomy", "Hemithyroidectomy", "With neck dissection"],
            "nerve_parathyroid": ["RLN identified and preserved", "Parathyroids preserved", "Parathyroid autotransplanted"],
        },
        "protocol": {
            "recovery_time": "Voice rest and lifting restriction about 10-14 days.",
            "medications": [
                "Paracetamol (NSAID if no contraindication); no routine antibiotics.",
                "Total thyroidectomy: start lifelong levothyroxine replacement.",
                "Check calcium / PTH; give oral calcium (and vitamin D) if hypocalcemia is symptomatic or biochemically confirmed.",
            ],
            "wound_care": [
                "Monitor the neck for swelling or hematoma; keep wound clean and dry; drain care if placed.",
            ],
            "diet_activity": [
                "Normal diet as soon as swallowing is comfortable.",
                "Voice rest and lifting restrictions for about 10-14 days.",
            ],
            "discharge_criteria": [
                "Airway stable with no neck swelling, calcium stable, swallowing comfortably; same day or next day.",
            ],
            "follow_up": ["Review calcium/PTH and thyroid function (TSH) at 4-6 weeks; histopathology review."],
            "red_flags": [
                "Neck swelling, stridor or difficulty breathing (hematoma, airway emergency)",
                "Numbness or tingling around mouth / fingers, muscle cramps (hypocalcemia)",
                "Persistent hoarse or weak voice (recurrent laryngeal nerve injury)",
                "Fever or wound infection",
            ],
        },
    },
]

_BY_ID = {p["id"]: p for p in PROCEDURES}


def get_procedure(procedure_id: str | None) -> dict | None:
    return _BY_ID.get(procedure_id or "")


def procedure_catalog() -> dict:
    """Everything the frontend needs to render intake and operative forms."""
    return {
        "common_intake": COMMON_INTAKE,
        "common_intraop": COMMON_INTRAOP,
        "procedures": [
            {k: p[k] for k in ("id", "name", "category", "symptoms", "intraop_extras")}
            for p in PROCEDURES
        ],
    }


def suggest_procedures(symptoms: list[str], free_text: str = "", limit: int = 3) -> list[dict]:
    """Rank procedures from selected symptoms using keyword overlap."""
    haystack = " ".join(symptoms + [free_text]).lower()
    scored = []
    for procedure in PROCEDURES:
        score = sum(2 for s in procedure["symptoms"] if s in symptoms)
        score += sum(1 for k in procedure["keywords"] if k in haystack)
        if score:
            scored.append((score, procedure))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {"id": p["id"], "name": p["name"], "category": p["category"], "score": score}
        for score, p in scored[:limit]
    ]
