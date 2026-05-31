"""
HFIP – CPV Code Filter
Maps Common Procurement Vocabulary (CPV) codes to healthcare relevance scores.
"""

from __future__ import annotations

from typing import Dict, List

# ─── CPV Score Map ────────────────────────────────────────────────────────────
# Key: CPV prefix (first 2-8 digits as string)
# Value: Score contribution

CPV_SCORES: Dict[str, int] = {
    # High relevance – IT + Health
    "72212": 15,   # Application software programming
    "72220": 15,   # Systems and technical consultancy services
    "72300": 12,   # Data services
    "72310": 12,   # Data processing services
    "72315": 12,   # Data network management
    "48180": 15,   # Medical software package
    "48814": 15,   # Medical information systems
    "85100": 12,   # Health services
    "85110": 12,   # Hospital and related services
    "85111": 12,   # Hospital services
    "73100": 12,   # R&D services
    "73110": 12,   # Research services
    "73200": 10,   # Research and development consultancy

    # Medium relevance
    "72000": 8,    # IT services
    "72200": 8,    # Software programming
    "73000": 8,    # R&D
    "85000": 8,    # Health and social work
    "48000": 6,    # Software packages
    "80400": 5,    # Adult and other education services
    "79000": 4,    # Business and management services
    "71300": 4,    # Engineering services (medical devices)

    # Lower relevance
    "85140": 5,    # Miscellaneous health services
    "85320": 5,    # Social services
    "66000": 3,    # Financial services (insurance)

    # Negative relevance – infrastructure / unrelated
    "45000": -20,  # Construction work
    "50000": -10,  # Repair and maintenance
    "55000": -15,  # Hotel, restaurant, retail
    "60000": -10,  # Transport
    "90000": -15,  # Sewage, refuse, sanitation
    "98000": -10,  # Membership organisation services
}


def score_cpv_codes(cpv_codes: List[str]) -> int:
    """
    Calculate aggregate score from a list of CPV code strings.
    Checks progressively shorter prefixes for a match.
    """
    if not cpv_codes:
        return 0

    total = 0
    matched = set()

    for code in cpv_codes:
        code_clean = str(code).replace("-", "").replace(" ", "")[:8]
        # Check from longest prefix to shortest (most specific first)
        for length in [8, 6, 5, 4, 2]:
            prefix = code_clean[:length]
            if prefix in CPV_SCORES and prefix not in matched:
                total += CPV_SCORES[prefix]
                matched.add(prefix)
                break  # Only count each code once

    return total


def is_healthcare_cpv(cpv_codes: List[str]) -> bool:
    """Quick boolean check whether any CPV code is healthcare-relevant."""
    score = score_cpv_codes(cpv_codes)
    return score > 0


# ─── Human-Readable CPV Labels ────────────────────────────────────────────────

CPV_LABELS: Dict[str, str] = {
    "72212": "Application Software Programming",
    "72220": "Systems & Technical Consultancy",
    "72300": "Data Services",
    "48180": "Medical Software Package",
    "48814": "Medical Information Systems",
    "85100": "Health Services",
    "85110": "Hospital Services",
    "73100": "R&D Services",
    "72000": "IT Services",
    "73000": "Research & Development",
    "85000": "Health & Social Work",
    "48000": "Software Packages",
    "45000": "Construction Work",
}


def get_cpv_label(code: str) -> str:
    code_clean = str(code)[:5]
    return CPV_LABELS.get(code_clean, f"CPV {code}")
