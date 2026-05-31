"""
HFIP – Department Topic Filter
Second-stage filter that maps tenders to specific department research topics.

The department focuses on Healthcare-AI / Digital Health, so we score and
classify tenders into the following topic buckets:

  1. Hospital Digitization / KHZG
  2. Clinical Decision Support / AI Diagnostics
  3. Medical Imaging AI
  4. Health Data & Interoperability (FHIR, KIS, EPA)
  5. Digital Health Applications (DiGA, mHealth, Telemedizin)
  6. Federated / Privacy-Preserving AI
  7. Natural Language Processing in Healthcare
  8. Predictive Analytics & Patient Monitoring
  9. Genomics / Precision Medicine
  10. General Healthcare Research Funding

Tenders that don't match any topic receive a department penalty (-20)
to discourage sending generic IT/health tenders to the LLM.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ─── Topic taxonomy ───────────────────────────────────────────────────────────

DEPARTMENT_TOPICS: Dict[str, Dict] = {
    "Hospital Digitization / KHZG": {
        "weight": 20,
        "keywords": [
            "khzg", "krankenhauszukunftsgesetz", "krankenhauszukunftsfonds",
            "klinik digitalisierung", "krankenhaus digitalisierung",
            "hospital digitization", "digitales krankenhaus",
            "elektronische patientenakte", "epa", "patientenakte",
            "klinisches informationssystem", "kis ", " kis,", " kis.",
            "krankenhausinformationssystem", "hospital information system",
            "e-health-gesetz", "digitalgesetz",
        ],
    },
    "Clinical Decision Support / AI Diagnostics": {
        "weight": 20,
        "keywords": [
            "clinical decision support", "klinische entscheidungsunterstützung",
            "diagnoseunterstützung", "ai diagnostics", "diagnostic ai",
            "clinical ai", "klinische ki", "medizinische ki",
            "sepsis detection", "sepsis erkennung",
            "risk prediction", "risikovorhersage",
            "früherkennung", "early detection", "early warning",
            "alert system", "warnsystem",
        ],
    },
    "Medical Imaging AI": {
        "weight": 20,
        "keywords": [
            "medical imaging", "medizinische bildgebung",
            "radiology ai", "radiologie ki", "radiologie software",
            "pathology ai", "pathologie ki",
            "ct scan", "mrt analyse", "mri analysis",
            "dicom", "pacs", "ris ",
            "image segmentation", "bildsegmentierung",
            "digital twin", "digitaler zwilling",
            "röntgen", "radiograph",
        ],
    },
    "Health Data & Interoperability": {
        "weight": 18,
        "keywords": [
            "fhir", "hl7", "hl7 fhir",
            "interoperabilität", "interoperability",
            "health data platform", "gesundheitsdatenplattform",
            "health data space", "ehds",
            "elektronische gesundheitsakte", "ehr integration",
            "ihe", "openehr",
            "datenstandardisierung", "data standardization",
            "health api", "gesundheits api",
            "gdng", "gematik",
        ],
    },
    "Digital Health Applications / DiGA": {
        "weight": 18,
        "keywords": [
            "diga", "digitale gesundheitsanwendung",
            "digitale therapie", "digital therapeutics",
            "mhealth", "m-health", "mobile health",
            "telemedizin", "telemedicine", "telehealth",
            "fernbehandlung", "remote patient monitoring",
            "patientenportal", "patient portal",
            "gesundheitsapp", "health app",
            "wearable", "tragbares gerät",
            "ambient assisted living", "aal",
        ],
    },
    "Federated / Privacy-Preserving AI": {
        "weight": 18,
        "keywords": [
            "federated learning", "föderiertes lernen",
            "federated machine learning",
            "differential privacy", "differentielle privatsphäre",
            "privacy-preserving", "datenschutz ki",
            "secure multi-party computation", "mpc",
            "homomorphic encryption",
            "distributed learning", "verteiltes lernen",
        ],
    },
    "NLP in Healthcare": {
        "weight": 17,
        "keywords": [
            "natural language processing", "nlp",
            "text mining", "textmining",
            "clinical text", "klinischer text",
            "clinical notes", "arztbriefe",
            "named entity recognition", "ner",
            "information extraction",
            "large language model", "llm",
            "sprachmodell", "language model",
            "discharge summary", "entlassungsbrief",
        ],
    },
    "Predictive Analytics & Patient Monitoring": {
        "weight": 17,
        "keywords": [
            "predictive analytics", "prädiktive analytik",
            "patient monitoring", "patientenmonitoring",
            "remote monitoring", "fernüberwachung",
            "readmission prediction", "wiederaufnahmevorhersage",
            "length of stay", "verweildauer",
            "patient flow", "patientenfluss",
            "bed management", "bettenbelegung",
            "vital signs", "vitalparameter",
            "iot health", "health iot",
        ],
    },
    "Genomics / Precision Medicine": {
        "weight": 16,
        "keywords": [
            "genomics", "genomik",
            "precision medicine", "präzisionsmedizin",
            "personalized medicine", "personalisierte medizin",
            "bioinformatics", "bioinformatik",
            "omics", "multi-omics",
            "oncology ai", "onkologie ki",
            "cancer registry", "krebsregister",
            "tumor", "mutationsanalyse",
        ],
    },
    "General Healthcare Research Funding": {
        "weight": 8,
        "keywords": [
            "forschungsförderung gesundheit", "health research funding",
            "innovationsfonds", "innovation fund",
            "g-ba innovation", "bmbf gesundheit",
            "bundesgesundheitsministerium", "bmg ",
            "gesundheitsforschung", "health research",
            "medizinische forschung", "medical research",
            "klinische studie", "clinical trial",
            "randomized controlled", "rct ",
        ],
    },
}

# Tenders that match none of the above get this score penalty
NO_TOPIC_MATCH_PENALTY = -20


# ─── Department Filter class ─────────────────────────────────────────────────

class DepartmentFilter:
    """
    Classifies a tender into department research topics and computes an
    additional topic relevance score on top of the keyword scorer.
    """

    def classify(self, tender: dict) -> Tuple[int, List[str]]:
        """
        Returns (topic_score, matched_topics).
        topic_score is added to the base keyword score before LLM evaluation.
        """
        text = (
            tender.get("title", "") + " " + tender.get("description", "")
        ).lower()

        matched_topics: List[str] = []
        topic_score = 0

        for topic_name, config in DEPARTMENT_TOPICS.items():
            weight = config["weight"]
            for kw in config["keywords"]:
                if kw.lower() in text:
                    # Award topic weight once per topic (not per keyword)
                    if topic_name not in matched_topics:
                        matched_topics.append(topic_name)
                        topic_score += weight
                    break  # one match per topic is enough

        if not matched_topics:
            topic_score += NO_TOPIC_MATCH_PENALTY

        return topic_score, matched_topics

    def get_primary_topic(self, tender: dict) -> Optional[str]:
        """Return the highest-matching topic name, or None."""
        text = (
            tender.get("title", "") + " " + tender.get("description", "")
        ).lower()

        best_topic: Optional[str] = None
        best_hits = 0

        for topic_name, config in DEPARTMENT_TOPICS.items():
            hits = sum(1 for kw in config["keywords"] if kw.lower() in text)
            if hits > best_hits:
                best_hits = hits
                best_topic = topic_name

        return best_topic if best_hits > 0 else None


# ─── Convenience singleton ────────────────────────────────────────────────────

department_filter = DepartmentFilter()
