"""Built-in demo corpus for GuruFlow ingestion.

The hackathon demo path must work with no uploads and no network, so the
Class 9 Electricity chapter ships as a structured, page-numbered corpus.
Page numbers match the numbers already used in ``demo-fixtures/`` so that
citations stay stable across the frontend, the planner and the fixtures.
"""

from __future__ import annotations

from typing import Any

DEMO_DOCUMENT_ID = "ncert-class9-science-ch12"

# Each section carries the page it came from so every generated Scene can cite
# a real location in the source material rather than a fabricated one.
DEMO_SECTIONS: list[dict[str, Any]] = [
    {
        "sectionId": "sec-electric-current",
        "pageOrSlide": 200,
        "heading": "Electric Current and Circuit",
        "excerpt": (
            "Electric current is expressed by the amount of charge flowing "
            "through a particular area in unit time."
        ),
        "keywords": [
            "current",
            "charge",
            "flow",
            "ampere",
            "electron",
            "electricity",
        ],
    },
    {
        "sectionId": "sec-circuit",
        "pageOrSlide": 201,
        "heading": "Electric Circuit",
        "excerpt": (
            "A continuous and closed path of an electric current is called an "
            "electric circuit."
        ),
        "keywords": ["circuit", "closed", "path", "battery", "wire", "bulb"],
    },
    {
        "sectionId": "sec-potential-difference",
        "pageOrSlide": 202,
        "heading": "Electric Potential and Potential Difference",
        "excerpt": (
            "Electric potential difference between two points in an electric "
            "circuit carrying some current as the work done to move a unit charge."
        ),
        "keywords": [
            "voltage",
            "potential",
            "difference",
            "volt",
            "work",
            "pressure",
        ],
    },
    {
        "sectionId": "sec-ohms-law",
        "pageOrSlide": 204,
        "heading": "Ohm's Law",
        "excerpt": (
            "The potential difference, V, across the ends of a given metallic "
            "wire in an electric circuit is directly proportional to the current "
            "flowing through it."
        ),
        "keywords": [
            "ohm",
            "law",
            "proportional",
            "voltage",
            "current",
            "resistance",
            "formula",
        ],
    },
    {
        "sectionId": "sec-resistance",
        "pageOrSlide": 204,
        "heading": "Resistance of a Conductor",
        "excerpt": (
            "It is the property of a conductor to resist the flow of charges "
            "through it."
        ),
        "keywords": ["resistance", "resist", "conductor", "ohm", "opposition"],
    },
    {
        "sectionId": "sec-resistance-current",
        "pageOrSlide": 205,
        "heading": "Current and Resistance Relationship",
        "excerpt": "If the resistance is doubled the current gets halved.",
        "keywords": [
            "resistance",
            "current",
            "doubled",
            "halved",
            "inverse",
            "decrease",
        ],
    },
    {
        "sectionId": "sec-inverse-proportionality",
        "pageOrSlide": 205,
        "heading": "Inverse Proportionality",
        "excerpt": (
            "It is obvious from Eq. (12.5) that the current through a resistor "
            "is inversely proportional to its resistance."
        ),
        "keywords": [
            "inversely",
            "proportional",
            "resistor",
            "current",
            "resistance",
        ],
    },
    {
        "sectionId": "sec-summary",
        "pageOrSlide": 206,
        "heading": "Summary",
        "excerpt": "Summary of Ohm's Law.",
        "keywords": ["summary", "revision", "recap", "ohm"],
    },
]
