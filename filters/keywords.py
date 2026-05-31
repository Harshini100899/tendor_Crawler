"""
HFIP – Keyword Dictionary
Positive / negative term weights for the pre-AI Healthcare AI scoring engine.
"""

from __future__ import annotations

from typing import Dict

# ─── Positive Keywords ────────────────────────────────────────────────────────
# Score points added when keyword is found in title or description.

POSITIVE_KEYWORDS: Dict[str, int] = {
    # Core AI / ML
    "artificial intelligence": 10,
    "künstliche intelligenz": 10,
    " ai ": 10,
    "machine learning": 10,
    "maschinelles lernen": 10,
    "deep learning": 10,
    "large language model": 10,
    "llm": 10,
    "neural network": 10,
    "natural language processing": 9,
    "nlp": 9,
    "computer vision": 9,

    # Clinical AI
    "clinical decision support": 10,
    "klinische entscheidungsunterstützung": 10,
    "predictive analytics": 9,
    "risk prediction": 9,
    "diagnostic ai": 10,
    "ai diagnostics": 10,

    # Digital Health
    "digital health": 9,
    "digitale gesundheit": 9,
    "digital medicine": 9,
    "digitale medizin": 9,
    "telehealth": 8,
    "telemedicine": 8,
    "telemedizin": 8,
    "ehealth": 8,
    "e-health": 8,
    "mhealth": 8,
    "m-health": 8,
    "diga": 9,  # Digitale Gesundheitsanwendung

    # Medical Imaging
    "medical imaging": 9,
    "medizinische bildgebung": 9,
    "radiology ai": 9,
    "pathology ai": 9,
    "image recognition": 8,

    # Health Data Standards
    "fhir": 8,
    "hl7": 8,
    "ehr": 8,
    "electronic health record": 8,
    "elektronische patientenakte": 8,
    "epa": 7,
    "health data": 8,
    "gesundheitsdaten": 8,
    "interoperability": 7,
    "interoperabilität": 7,

    # Analytics / Informatics
    "healthcare analytics": 8,
    "health analytics": 8,
    "biomedical informatics": 8,
    "bioinformatics": 8,
    "bioinformatik": 8,
    "clinical informatics": 8,
    "population health": 7,
    "epidemiology": 6,
    "genomics": 7,
    "precision medicine": 8,
    "personalized medicine": 8,

    # Infrastructure / Platforms
    "health platform": 7,
    "health cloud": 7,
    "health api": 7,
    "hospital information system": 7,
    "krankenhausinformationssystem": 7,
    "kis": 6,

    # Research / Innovation
    "forschung": 5,
    "research": 5,
    "innovation": 5,
    "förderung": 4,
    "funding": 4,
    "grant": 4,

    # Healthcare context
    "hospital": 6,
    "krankenhaus": 6,
    "klinik": 6,
    "clinic": 6,
    "healthcare": 7,
    "gesundheitsversorgung": 7,
    "patient": 5,
    "medical": 5,
    "medizin": 5,
    "pharma": 4,
    "biotech": 5,
}

# ─── Negative Keywords ────────────────────────────────────────────────────────
# Score points subtracted when keyword is found.

NEGATIVE_KEYWORDS: Dict[str, int] = {
    # Construction / Facility
    "construction": -25,
    "bauleistung": -25,
    "bauarbeiten": -25,
    "neubau": -20,
    "umbau": -20,
    "renovation": -20,
    "renovierung": -20,
    "sanierung": -20,
    "building": -20,
    "gebäude": -15,

    # Cleaning / Facility Management
    "cleaning": -20,
    "reinigung": -20,
    "facility management": -20,
    "hausmeister": -15,
    "hausreinigung": -20,
    "gebäudereinigung": -20,

    # Security (physical)
    "security guard": -20,
    "wachdienst": -20,
    "bewachung": -20,
    "sicherheitsdienst": -20,

    # Furniture / Equipment
    "furniture": -15,
    "möbel": -15,
    "büromöbel": -15,
    "ausstattung": -10,

    # Catering / Food
    "catering": -15,
    "verpflegung": -15,
    "speisen": -10,
    "kantinenbetrieb": -15,

    # Printing / Office Supplies
    "druckerzeugnisse": -15,
    "bürobedarf": -10,
    "papier": -10,
    "printing": -10,

    # Transport / Logistics
    "transport": -10,
    "logistik": -10,
    "lieferdienst": -10,
    "kurier": -10,

    # Waste
    "entsorgung": -15,
    "abfallentsorgung": -15,
    "waste disposal": -15,

    # Gardening / Landscaping
    "gartenarbeit": -15,
    "grünpflege": -15,
    "landscaping": -15,
}
