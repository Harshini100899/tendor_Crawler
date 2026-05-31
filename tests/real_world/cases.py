"""
HFIP – Real-World Test Cases
25 cases modelled on genuine TED/Bund/G-BA notices (titles, descriptions, CPV codes,
organizations are real or closely paraphrased from public procurement databases).

Structure:
  - RELEVANT_CASES   : 15 healthcare-AI tenders that SHOULD score ≥ 60
  - IRRELEVANT_CASES : 10 tenders that SHOULD score < 40 and be rejected by AI

Each case dict matches the normalized tender schema used throughout the pipeline.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone

_now = datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# RELEVANT CASES  (expected AI relevant=True, score ≥ 60)
# ─────────────────────────────────────────────────────────────────────────────

RELEVANT_CASES: list[dict] = [
    # ── 1. TED – German university hospital, AI clinical decision support ────
    {
        "case_id": "RW-001",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "Entwicklung einer KI-basierten klinischen Entscheidungsunterstützung für Intensivstationen",
        "description": (
            "Das Universitätsklinikum Frankfurt sucht einen Auftragnehmer zur Entwicklung und "
            "Implementierung einer Machine-Learning-Plattform zur Sepsis-Frühwarnung auf der "
            "Intensivstation. Die Lösung soll FHIR R4-kompatibel sein, bestehende KIS-Systeme "
            "anbinden und Echtzeit-Risikoscores für behandelnde Ärzte bereitstellen. Erwartet "
            "werden Kenntnisse in Python/TensorFlow, HL7 FHIR, datenschutzkonformes Deployment "
            "on-premise (BSI-Grundschutz). Projektlaufzeit: 24 Monate."
        ),
        "organization": "Universitätsklinikum Frankfurt am Main",
        "country": "DE",
        "deadline": _now + timedelta(days=42),
        "published_date": _now - timedelta(days=3),
        "url": "https://ted.europa.eu/en/notice/2026-OJS089-234567/general-information",
        "cpv_codes": ["72212000", "85100000", "72310000"],
    },

    # ── 2. TED – NHS England, AI radiology reading platform ─────────────────
    {
        "case_id": "RW-002",
        "expected_relevant": True,
        "expected_min_score": 65,
        "source": "ted",
        "title": "AI-Assisted Diagnostic Imaging Platform for NHS Radiology Departments",
        "description": (
            "NHS England invites tenders for an AI-assisted radiology platform capable of "
            "automated triage and preliminary reads for chest X-rays, CT head, and mammography. "
            "The system must achieve CE marking (Class IIa MDR), integrate with RIS/PACS via "
            "DICOM, and support explainable AI (XAI) outputs. Performance benchmarks: AUC ≥ 0.92 "
            "on NHS validation datasets. Cloud-agnostic deployment required (Azure/AWS/on-prem). "
            "Framework contract, 4 years, estimated value £24M."
        ),
        "organization": "NHS England – Commercial Directorate",
        "country": "GB",
        "deadline": _now + timedelta(days=55),
        "published_date": _now - timedelta(days=2),
        "url": "https://ted.europa.eu/en/notice/2026-OJS091-241890/general-information",
        "cpv_codes": ["85150000", "72212000", "48814000"],
    },

    # ── 3. G-BA Innovationsfonds – digital health coaching for chronic disease ─
    {
        "case_id": "RW-003",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "gba",
        "title": "Digitale Gesundheitscoaching-App mit KI für Typ-2-Diabetes-Patienten (G-BA Innovationsfonds)",
        "description": (
            "Förderaufruf für ein Forschungsprojekt zur Entwicklung und Evaluation einer "
            "KI-gestützten mobilen Gesundheitscoaching-Anwendung für Menschen mit Typ-2-Diabetes. "
            "Die App soll personalisierte Ernährungs- und Bewegungsempfehlungen auf Basis von "
            "CGM-Daten, Wearable-Sensoren und Natural Language Processing generieren. "
            "Voraussetzung: Zulassung als DiGA (Digitale Gesundheitsanwendung) nach §33a SGB V. "
            "Förderhöhe: bis 2,5 Mio. EUR, Laufzeit 36 Monate."
        ),
        "organization": "Gemeinsamer Bundesausschuss (G-BA)",
        "country": "DE",
        "deadline": _now + timedelta(days=68),
        "published_date": _now - timedelta(days=5),
        "url": "https://innovationsfonds.g-ba.de/foerderbekanntmachung/2026-diabetes-ki",
        "cpv_codes": ["85100000", "72212000", "85140000"],
    },

    # ── 4. BMBF – federated learning for oncology data ───────────────────────
    {
        "case_id": "RW-004",
        "expected_relevant": True,
        "expected_min_score": 70,
        "source": "bmftr",
        "title": "Föderiertes Lernen für die Onkologie-Diagnostik – BMBF Forschungsförderung",
        "description": (
            "Das BMBF schreibt Fördermittel für Verbundprojekte aus, die Federated Learning "
            "Methoden zur datenschutzwahrenden Analyse onkologischer Bilddaten entwickeln. "
            "Anträge sollen KI-Modelle für die Früherkennung von Lungen-, Darm- oder Brustkrebs "
            "erproben, ohne Patientendaten aus Klinikverbünden herauszugeben. Kooperationen mit "
            "mindestens zwei Universitätskliniken und einem Industriepartner sind Pflicht. "
            "Fördervolumen je Verbund: 3–5 Mio. EUR."
        ),
        "organization": "Bundesministerium für Forschung, Technologie und Raumfahrt (BMFTR)",
        "country": "DE",
        "deadline": _now + timedelta(days=90),
        "published_date": _now - timedelta(days=1),
        "url": "https://foerderportal.bund.de/foerderbekanntmachung/2026-federated-onco",
        "cpv_codes": ["73100000", "72212000", "85121200"],
    },

    # ── 5. TED – Belgium hospital, NLP for EHR structured data extraction ────
    {
        "case_id": "RW-005",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "NLP-Based Clinical Text Mining and Structured Data Extraction from EHR",
        "description": (
            "UZ Leuven invites proposals for an NLP pipeline to extract structured clinical "
            "information from free-text physician notes, discharge summaries, and radiology "
            "reports. The system must handle multilingual text (Dutch/French/English), integrate "
            "with the hospital's Epic EHR via FHIR R4 APIs, and comply with GDPR and NIS2. "
            "Use cases: automated ICD-10 coding, adverse event detection, cohort identification "
            "for clinical trials. Pilot phase: 6 months, full rollout: 18 months."
        ),
        "organization": "Universitaire Ziekenhuizen Leuven (UZ Leuven)",
        "country": "BE",
        "deadline": _now + timedelta(days=35),
        "published_date": _now - timedelta(days=4),
        "url": "https://ted.europa.eu/en/notice/2026-OJS088-229341/general-information",
        "cpv_codes": ["72212000", "72310000", "85100000"],
    },

    # ── 6. TED – Sweden region, predictive analytics for patient flow ────────
    {
        "case_id": "RW-006",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "Predictive Analytics Platform for Hospital Patient Flow and Bed Management",
        "description": (
            "Region Stockholm procures a predictive analytics solution to forecast patient "
            "admissions, length of stay, and discharge timing across 14 acute hospitals. "
            "The platform must use machine learning on historical EHR data, integrate with "
            "TakeCare EPR, and provide dashboards for bed managers and operations teams. "
            "GDPR-compliant data processing, Swedish cloud hosting preferred. "
            "4-year framework, estimated SEK 48M."
        ),
        "organization": "Region Stockholm – Upphandlingsenheten",
        "country": "SE",
        "deadline": _now + timedelta(days=47),
        "published_date": _now - timedelta(days=6),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-237812/general-information",
        "cpv_codes": ["72212000", "72310000", "85111000"],
    },

    # ── 7. TED – EU Commission, AI health surveillance platform ─────────────
    {
        "case_id": "RW-007",
        "expected_relevant": True,
        "expected_min_score": 65,
        "source": "ted",
        "title": "European AI-Powered Infectious Disease Surveillance and Early Warning System",
        "description": (
            "The European Centre for Disease Prevention and Control (ECDC) procures an "
            "AI-powered epidemiological surveillance platform to integrate multi-source data "
            "(syndromic surveillance, genomic sequencing, social media signals) and generate "
            "early warnings for infectious disease outbreaks. LLM-based anomaly detection and "
            "automated situation reports are required. Interoperability with WHO GOARN and "
            "national health authorities. 3-year contract, €8.5M."
        ),
        "organization": "European Centre for Disease Prevention and Control (ECDC)",
        "country": "SE",
        "deadline": _now + timedelta(days=61),
        "published_date": _now - timedelta(days=2),
        "url": "https://ted.europa.eu/en/notice/2026-OJS091-240023/general-information",
        "cpv_codes": ["72212000", "73000000", "85140000"],
    },

    # ── 8. TED – Austria, digital twin for surgical planning ─────────────────
    {
        "case_id": "RW-008",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "KI-gestützte digitale Zwillinge für präoperative Planung in der Herzchirurgie",
        "description": (
            "Das AKH Wien sucht einen Entwicklungspartner für patientenspezifische digitale "
            "Zwillinge auf Basis von CT/MRT-Daten zur präoperativen Planung komplexer "
            "Herzoperationen. Die KI-Komponente soll automatische Segmentierung und "
            "biomechanische Simulation ermöglichen. Schnittstellen: DICOM, HL7 FHIR. "
            "CE-Klassifizierung: Klasse IIb nach MDR. Projektvolumen: 1,8 Mio. EUR."
        ),
        "organization": "Allgemeines Krankenhaus der Stadt Wien (AKH Wien)",
        "country": "AT",
        "deadline": _now + timedelta(days=38),
        "published_date": _now - timedelta(days=7),
        "url": "https://ted.europa.eu/en/notice/2026-OJS087-226554/general-information",
        "cpv_codes": ["85100000", "72212000", "48814000"],
    },

    # ── 9. TED – Netherlands, AI remote patient monitoring ───────────────────
    {
        "case_id": "RW-009",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "AI-Driven Remote Patient Monitoring Platform for Heart Failure Patients",
        "description": (
            "Amsterdam UMC seeks a vendor to deploy an AI-driven remote monitoring system for "
            "patients with chronic heart failure. The solution must collect continuous vital signs "
            "via wearables, apply ML algorithms to detect decompensation early, and trigger "
            "automated alerts to clinical teams via EHR integration (Chipsoft HIX/FHIR). "
            "Privacy by design (Dutch GDPR), CE MDR Class IIa certified. "
            "Pilot: 500 patients; scale-up: 5,000 patients over 3 years."
        ),
        "organization": "Amsterdam UMC – Procurement Department",
        "country": "NL",
        "deadline": _now + timedelta(days=44),
        "published_date": _now - timedelta(days=3),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-238901/general-information",
        "cpv_codes": ["85111000", "72212000", "33182200"],
    },

    # ── 10. Bund – BMBF, mental health NLP chatbot research grant ────────────
    {
        "case_id": "RW-010",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "bund",
        "title": "Förderaufruf: KI-basierte Frühintervention bei psychischen Erkrankungen (Chatbot / NLP)",
        "description": (
            "Das BMBF fördert Forschungsvorhaben zur Entwicklung KI-gestützter "
            "Frühinterventionssysteme bei Depressionen und Angststörungen. Gesucht werden "
            "Projekte, die Large Language Models und Sentiment-Analyse einsetzen, um gefährdete "
            "Personen frühzeitig zu erkennen und evidenzbasierte Interventionen anzubieten. "
            "Datenschutz (§22 BDSG), ärztliche Aufsicht und klinische Validierung sind "
            "Pflichtbestandteile. Förderhöhe: bis 1,5 Mio. EUR pro Projekt."
        ),
        "organization": "Bundesministerium für Forschung, Technologie und Raumfahrt (BMFTR)",
        "country": "DE",
        "deadline": _now + timedelta(days=75),
        "published_date": _now - timedelta(days=2),
        "url": "https://foerderportal.bund.de/foerderbekanntmachung/2026-mental-health-ki",
        "cpv_codes": ["85311000", "72212000", "73100000"],
    },

    # ── 11. TED – Poland, national cancer registry AI ────────────────────────
    {
        "case_id": "RW-011",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "Wdrożenie systemu analityki AI dla Krajowego Rejestru Nowotworów",
        "description": (
            "Narodowy Instytut Onkologii zaprasza do składania ofert na wdrożenie platformy "
            "analitycznej opartej na sztucznej inteligencji dla Krajowego Rejestru Nowotworów. "
            "System ma umożliwiać predykcję przeżywalności, identyfikację anomalii w danych "
            "rejestrowych i automatyczne generowanie raportów epidemiologicznych. Wymagana "
            "integracja z systemem P1 (CSIOZ) oraz zgodność z RODO. Wartość: 4,2 mln PLN."
        ),
        "organization": "Narodowy Instytut Onkologii im. Marii Skłodowskiej-Curie",
        "country": "PL",
        "deadline": _now + timedelta(days=33),
        "published_date": _now - timedelta(days=5),
        "url": "https://ted.europa.eu/en/notice/2026-OJS089-231100/general-information",
        "cpv_codes": ["85121200", "72212000", "72310000"],
    },

    # ── 12. TED – France, AI drug interaction checker for hospital pharmacy ──
    {
        "case_id": "RW-012",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "Système d'aide à la décision médicamenteuse basé sur l'IA pour pharmacies hospitalières",
        "description": (
            "L'AP-HP (Assistance Publique – Hôpitaux de Paris) recherche une solution d'aide à "
            "la décision médicamenteuse intégrant l'intelligence artificielle pour détecter les "
            "interactions médicamenteuses, les contre-indications et les erreurs de dosage. "
            "La solution doit s'interfacer avec Orbis (DPI), respecter le RGPD et la "
            "réglementation européenne sur les dispositifs médicaux (MDR 2017/745). "
            "Durée du marché : 4 ans, valeur estimée : 6,5 M€."
        ),
        "organization": "Assistance Publique – Hôpitaux de Paris (AP-HP)",
        "country": "FR",
        "deadline": _now + timedelta(days=51),
        "published_date": _now - timedelta(days=4),
        "url": "https://ted.europa.eu/en/notice/2026-OJS091-239440/general-information",
        "cpv_codes": ["85149000", "72212000", "48814000"],
    },

    # ── 13. TED – Spain, AI genomics platform for precision oncology ─────────
    {
        "case_id": "RW-013",
        "expected_relevant": True,
        "expected_min_score": 65,
        "source": "ted",
        "title": "Plataforma de IA para Medicina de Precisión y Análisis Genómico en Oncología",
        "description": (
            "El Hospital Universitario Vall d'Hebron lanza un concurso para una plataforma de "
            "inteligencia artificial orientada al análisis de datos genómicos tumorales (WGS/WES), "
            "integración de datos ómicos y datos clínicos (EHR), y generación de recomendaciones "
            "terapéuticas personalizadas basadas en evidencia. El sistema deberá cumplir el "
            "Reglamento UE de IA (IA Act, Clase Alto Riesgo) y MDR 2017/745. "
            "Presupuesto estimado: 3,1 M€, plazo 36 meses."
        ),
        "organization": "Hospital Universitario Vall d'Hebron",
        "country": "ES",
        "deadline": _now + timedelta(days=58),
        "published_date": _now - timedelta(days=3),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-237005/general-information",
        "cpv_codes": ["85121200", "72212000", "73100000"],
    },

    # ── 14. TED – Denmark, federated EHR analytics across 5 regions ─────────
    {
        "case_id": "RW-014",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "ted",
        "title": "Federated Machine Learning Infrastructure for Cross-Regional EHR Analysis in Denmark",
        "description": (
            "Sundhedsdatastyrelsen (Danish Health Data Authority) procures a federated machine "
            "learning infrastructure to enable joint model training across the five Danish "
            "regions' EHR systems without centralising patient data. The system must support "
            "differential privacy, MPC protocols, and integrate with MedCom messaging standards. "
            "Target use cases: readmission prediction, medication adherence, population health. "
            "Framework contract: 5 years, estimated DKK 35M."
        ),
        "organization": "Sundhedsdatastyrelsen (Danish Health Data Authority)",
        "country": "DK",
        "deadline": _now + timedelta(days=70),
        "published_date": _now - timedelta(days=1),
        "url": "https://ted.europa.eu/en/notice/2026-OJS092-244500/general-information",
        "cpv_codes": ["72212000", "73000000", "85100000"],
    },

    # ── 15. G-BA – AI-supported rehabilitation after stroke ──────────────────
    {
        "case_id": "RW-015",
        "expected_relevant": True,
        "expected_min_score": 60,
        "source": "gba",
        "title": "Förderaufruf: KI-gestützte Rehabilitation nach Schlaganfall mit sensorbasiertem Feedback",
        "description": (
            "G-BA Innovationsfonds fördert Projekte zur Entwicklung und Evaluation eines "
            "KI-basierten Rehabilitationssystems für Schlaganfallpatienten. Das System soll "
            "Bewegungssensoren und Computer Vision nutzen, um Übungsausführung zu bewerten, "
            "Therapiepläne adaptiv anzupassen und Therapeuten sowie Patienten Echtzeit-Feedback "
            "zu geben. Evaluation via randomisiert-kontrollierte Studie. Fördersumme: 2 Mio. EUR."
        ),
        "organization": "Gemeinsamer Bundesausschuss (G-BA)",
        "country": "DE",
        "deadline": _now + timedelta(days=85),
        "published_date": _now - timedelta(days=6),
        "url": "https://innovationsfonds.g-ba.de/foerderbekanntmachung/2026-stroke-rehab-ki",
        "cpv_codes": ["85100000", "72212000", "85140000"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# IRRELEVANT CASES  (expected AI relevant=False, score < 40)
# ─────────────────────────────────────────────────────────────────────────────

IRRELEVANT_CASES: list[dict] = [
    # ── I-1. TED – Office supplies tender ────────────────────────────────────
    {
        "case_id": "IRR-001",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "bund",
        "title": "Rahmenvertrag Bürobedarf und Druckerzeugnisse für Bundesbehörden 2026",
        "description": (
            "Beschaffung von Büromaterialien, Papier, Druckerzeugnissen, Briefumschlägen und "
            "Büroausstattung für Bundesministerien und nachgeordnete Behörden im Rahmen eines "
            "mehrjährigen Rahmenvertrags. Lose: Papier/Karton, Schreibwaren, Toner/Tintenpatronen."
        ),
        "organization": "Beschaffungsamt des BMI",
        "country": "DE",
        "deadline": _now + timedelta(days=21),
        "published_date": _now - timedelta(days=2),
        "url": "https://www.bund.de/SubPortal/DE/Vergabe/2026-buerobedarf.html",
        "cpv_codes": ["30192000", "22000000"],
    },

    # ── I-2. TED – Road maintenance works ────────────────────────────────────
    {
        "case_id": "IRR-002",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Straßenunterhaltung und Fahrbahnmarkierungsarbeiten BAB A9 2026–2028",
        "description": (
            "Die Autobahn GmbH des Bundes schreibt Unterhaltungsarbeiten für die Bundesautobahn "
            "A9 aus, einschließlich Deckenerneuerung, Markierungsarbeiten, Schutzplankenreparatur "
            "und Brückeninspektionen. Losvergabe nach STLB-Bau."
        ),
        "organization": "Die Autobahn GmbH des Bundes – Niederlassung Bayern",
        "country": "DE",
        "deadline": _now + timedelta(days=30),
        "published_date": _now - timedelta(days=4),
        "url": "https://ted.europa.eu/en/notice/2026-OJS088-228100/general-information",
        "cpv_codes": ["45233141", "45233221"],
    },

    # ── I-3. TED – School catering services ──────────────────────────────────
    {
        "case_id": "IRR-003",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Schulverpflegung und Cateringdienstleistungen für Berliner Grundschulen",
        "description": (
            "Der Senat Berlin vergibt Cateringdienstleistungen für die warme Mittagsverpflegung "
            "an 142 Berliner Grundschulen. Anforderungen: Bio-Anteil ≥ 30 %, vegetarische Option "
            "täglich, Allergenmanagement, Anlieferung in Warmhaltebehältern."
        ),
        "organization": "Senatsverwaltung für Bildung, Jugend und Familie Berlin",
        "country": "DE",
        "deadline": _now + timedelta(days=25),
        "published_date": _now - timedelta(days=3),
        "url": "https://ted.europa.eu/en/notice/2026-OJS087-225500/general-information",
        "cpv_codes": ["55523100", "55520000"],
    },

    # ── I-4. TED – Fleet vehicle procurement ─────────────────────────────────
    {
        "case_id": "IRR-004",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Procurement of Electric Vehicles for Government Fleet – Ministry of Finance Ireland",
        "description": (
            "The Office of Government Procurement invites tenders for the supply of battery "
            "electric vehicles (BEV) for the Irish Government fleet. Lot 1: passenger cars; "
            "Lot 2: light commercial vans. Requirements include minimum range 400 km WLTP, "
            "vehicle tracking, and whole-life cost analysis."
        ),
        "organization": "Office of Government Procurement – Ireland",
        "country": "IE",
        "deadline": _now + timedelta(days=28),
        "published_date": _now - timedelta(days=5),
        "url": "https://ted.europa.eu/en/notice/2026-OJS089-230500/general-information",
        "cpv_codes": ["34110000", "34136000"],
    },

    # ── I-5. TED – Building cleaning services ────────────────────────────────
    {
        "case_id": "IRR-005",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Reinigungsdienstleistungen für Bundesverwaltungsgebäude – Bonn und Berlin",
        "description": (
            "Das Bundesamt für zentrale Dienste schreibt Gebäudereinigung und Glasreinigung "
            "für Liegenschaften in Bonn (ca. 25.000 m²) und Berlin (ca. 18.000 m²) aus. "
            "Leistungsverzeichnis umfasst Unterhalts-, Grund- und Glasreinigung, Winterdienst."
        ),
        "organization": "Bundesamt für zentrale Dienste und offene Vermögensfragen",
        "country": "DE",
        "deadline": _now + timedelta(days=19),
        "published_date": _now - timedelta(days=6),
        "url": "https://ted.europa.eu/en/notice/2026-OJS087-224100/general-information",
        "cpv_codes": ["90919200", "90911200"],
    },

    # ── I-6. TED – IT hardware procurement (non-health) ──────────────────────
    {
        "case_id": "IRR-006",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Lieferung von Desktop-PCs, Notebooks und Monitoren für Finanzbehörden",
        "description": (
            "Zollverwaltung Deutschland beschafft 4.500 Desktop-Computer, 2.200 Notebooks und "
            "6.000 Monitore für Büroarbeitsplätze in Zolldienststellen bundesweit. "
            "Rahmenvertrag 3 Jahre, Lieferung auf Abruf, IT-Grundschutz-Konformität erforderlich."
        ),
        "organization": "Generalzolldirektion – Referat Z23",
        "country": "DE",
        "deadline": _now + timedelta(days=32),
        "published_date": _now - timedelta(days=2),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-236200/general-information",
        "cpv_codes": ["30213000", "30213100", "30231300"],
    },

    # ── I-7. TED – Landscaping and park maintenance ───────────────────────────
    {
        "case_id": "IRR-007",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Garten- und Landschaftspflegearbeiten für städtische Grünanlagen München",
        "description": (
            "Landeshauptstadt München, Baureferat, vergibt Pflege- und Unterhaltungsarbeiten "
            "für öffentliche Grünanlagen, Straßenbäume und Spielplätze im Stadtgebiet. "
            "Gesamtfläche ca. 4.200 ha. Rahmenvertrag 5 Jahre."
        ),
        "organization": "Landeshauptstadt München – Baureferat",
        "country": "DE",
        "deadline": _now + timedelta(days=23),
        "published_date": _now - timedelta(days=8),
        "url": "https://ted.europa.eu/en/notice/2026-OJS086-220500/general-information",
        "cpv_codes": ["77310000", "77314000"],
    },

    # ── I-8. TED – Security guarding services ────────────────────────────────
    {
        "case_id": "IRR-008",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Security and Access Control Services for European Commission Buildings Brussels",
        "description": (
            "The European Commission, OIB, procures physical security and access control "
            "services for 22 Commission buildings in Brussels. Services include manned guarding, "
            "reception/visitor management, CCTV monitoring, and alarm response. "
            "Contract value: €45M over 4 years."
        ),
        "organization": "European Commission – Office for Infrastructure and Logistics Brussels",
        "country": "BE",
        "deadline": _now + timedelta(days=40),
        "published_date": _now - timedelta(days=3),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-237900/general-information",
        "cpv_codes": ["79713000", "79710000"],
    },

    # ── I-9. TED – Legal translation services ────────────────────────────────
    {
        "case_id": "IRR-009",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Legal and Administrative Translation Services for EU Council Presidency 2026",
        "description": (
            "The Council of the EU procures legal and administrative translation services "
            "covering all 24 EU official languages. Services include document translation, "
            "revision, post-editing of machine translation output, and terminology management. "
            "Framework contract: 2 years + 2 optional extensions."
        ),
        "organization": "General Secretariat of the Council of the EU",
        "country": "BE",
        "deadline": _now + timedelta(days=36),
        "published_date": _now - timedelta(days=5),
        "url": "https://ted.europa.eu/en/notice/2026-OJS089-232700/general-information",
        "cpv_codes": ["79530000", "79540000"],
    },

    # ── I-10. TED – Civil engineering bridge construction ────────────────────
    {
        "case_id": "IRR-010",
        "expected_relevant": False,
        "expected_min_score": 0,
        "source": "ted",
        "title": "Neubau Eisenbahnbrücke Rheinquerung Köln-Mülheim – Planungsleistungen",
        "description": (
            "Deutsche Bahn Netz AG schreibt Planungsleistungen (Vorentwurf bis Ausführungsplanung, "
            "Leistungsphasen 2–5 HOAI) für den Neubau einer zweigleisigen Eisenbahnbrücke über "
            "den Rhein bei Köln-Mülheim aus. Gesamtbaulänge ca. 670 m, Tragwerk Stahl-Verbund."
        ),
        "organization": "DB InfraGO AG – Bereich Großprojekte Brücken",
        "country": "DE",
        "deadline": _now + timedelta(days=45),
        "published_date": _now - timedelta(days=4),
        "url": "https://ted.europa.eu/en/notice/2026-OJS090-238400/general-information",
        "cpv_codes": ["71322300", "45221119"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Combined list
# ─────────────────────────────────────────────────────────────────────────────

ALL_CASES: list[dict] = RELEVANT_CASES + IRRELEVANT_CASES
