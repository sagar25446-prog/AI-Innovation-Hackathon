"""Concept catalogue for the Class 9 Electricity path.

Each concept carries its narration in all three supported languages plus the
extra depth added for higher levels, the retrieval query used to find its
citations, and a visual specification. The visual shapes mirror the templates
in ``services/visuals`` so the frontend renders backend scenes and Person 3's
fixtures through the same components.
"""

from __future__ import annotations

from typing import Any

# Lower priority number == more essential. Used to drop scenes when the
# learner's time budget is small.
CONCEPTS: list[dict[str, Any]] = [
    {
        "id": "intro-electricity",
        "priority": 3,
        "baseSeconds": 30,
        "query": "electric current circuit electricity charge",
        "objective": {
            "english": "Welcome and introduce the electricity topic",
            "hindi": "स्वागत और विद्युत विषय का परिचय",
            "hinglish": "Welcome and introduce electricity topic",
        },
        "narration": {
            "english": (
                "Hello students! Today we will learn about Electric Current and "
                "Ohm's Law. This is the basic rule of electricity."
            ),
            "hindi": (
                "नमस्ते विद्यार्थियों! आज हम विद्युत धारा और ओम के नियम के बारे में "
                "सीखेंगे। यह बिजली का बुनियादी नियम है।"
            ),
            "hinglish": (
                "Hello students! Aaj hum Electric Current aur Ohm's Law ke baare "
                "mein seekhenge. Yeh electricity ka basic rule hai."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "We will connect each idea to its SI unit as we go.",
                "advanced": "We will also look at where the linear V-I relation stops holding.",
            },
            "hindi": {
                "intermediate": "हम हर विचार को उसकी SI इकाई से जोड़ेंगे।",
                "advanced": "हम यह भी देखेंगे कि V-I का रैखिक संबंध कहाँ लागू नहीं होता।",
            },
            "hinglish": {
                "intermediate": "Har concept ko uski SI unit ke saath connect karenge.",
                "advanced": "Yeh bhi dekhenge ki linear V-I relation kahan fail hota hai.",
            },
        },
        "visual": {
            "type": "concept_map",
            "data": {
                "nodes": [
                    {"id": "i", "label": "Electric Current", "type": "concept"},
                    {"id": "v", "label": "Voltage", "type": "concept"},
                    {"id": "r", "label": "Resistance", "type": "concept"},
                    {"id": "ohm", "label": "Ohm's Law", "type": "formula"},
                ],
                "edges": [
                    {"from": "ohm", "to": "v", "label": "defines"},
                    {"from": "ohm", "to": "i", "label": "defines"},
                    {"from": "ohm", "to": "r", "label": "defines"},
                ],
                "layout": "hierarchical",
            },
        },
    },
    {
        "id": "electric-current",
        "priority": 1,
        "baseSeconds": 45,
        "query": "current charge flow ampere circuit closed path",
        "objective": {
            "english": "Explain what electric current is",
            "hindi": "विद्युत धारा क्या है, यह समझाना",
            "hinglish": "Explain what electric current is",
        },
        "narration": {
            "english": (
                "Today we will learn about Electric Current. Current means the "
                "flow of electricity, just like water flowing in a river."
            ),
            "hindi": (
                "आज हम विद्युत धारा के बारे में सीखेंगे। धारा का मतलब है बिजली का "
                "बहाव, बिल्कुल नदी में बहते पानी की तरह।"
            ),
            "hinglish": (
                "Aaj hum Electric Current ke baare mein seekhenge. Current matlab "
                "electricity ka flow hai, bilkul paani ki nadiya ki tarah."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "Formally, I = Q/t, and current is measured in amperes.",
                "advanced": "Conventional current opposes the actual drift of electrons.",
            },
            "hindi": {
                "intermediate": "औपचारिक रूप से, I = Q/t, और धारा एम्पियर में मापी जाती है।",
                "advanced": "पारंपरिक धारा की दिशा इलेक्ट्रॉन के वास्तविक बहाव के विपरीत होती है।",
            },
            "hinglish": {
                "intermediate": "Formally, I = Q/t hota hai, aur current amperes mein measure hoti hai.",
                "advanced": "Conventional current ki direction electrons ke actual drift ke opposite hoti hai.",
            },
        },
        "visual": {
            "type": "circuit",
            "data": {
                "components": [
                    {"type": "battery", "label": "V = 10V"},
                    {"type": "wire", "label": "conductor"},
                    {"type": "bulb", "label": "load"},
                ],
                "connections": [
                    {"from": "battery", "to": "wire"},
                    {"from": "wire", "to": "bulb"},
                    {"from": "bulb", "to": "battery"},
                ],
                "annotations": ["Current flows from + to -"],
                "highlight": "current-flow",
            },
        },
    },
    {
        "id": "voltage",
        "priority": 2,
        "baseSeconds": 45,
        "query": "voltage potential difference volt work pressure",
        "objective": {
            "english": "Explain what voltage is",
            "hindi": "वोल्टेज क्या है, यह समझाना",
            "hinglish": "Explain what voltage is",
        },
        "narration": {
            "english": (
                "Think of voltage like water pressure - the more pressure, the "
                "more current flows. It pushes the electrons along."
            ),
            "hindi": (
                "वोल्टेज को पानी के दबाव की तरह समझो - जितना ज़्यादा दबाव, उतनी "
                "ज़्यादा धारा बहेगी। यह इलेक्ट्रॉन को धक्का देता है।"
            ),
            "hinglish": (
                "Voltage ko samjho jaise water pressure - jitna zyada pressure, "
                "utna zyada current flow hoga. Yeh electrons ko push karta hai."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "It is the work done per unit charge, measured in volts.",
                "advanced": "One volt is one joule of work per coulomb of charge moved.",
            },
            "hindi": {
                "intermediate": "यह प्रति इकाई आवेश किया गया कार्य है, वोल्ट में मापा जाता है।",
                "advanced": "एक वोल्ट का अर्थ है एक कूलॉम आवेश पर एक जूल कार्य।",
            },
            "hinglish": {
                "intermediate": "Yeh per unit charge kiya gaya work hai, volts mein measure hota hai.",
                "advanced": "Ek volt matlab ek coulomb charge par ek joule ka work.",
            },
        },
        "visual": {
            "type": "circuit",
            "data": {
                "components": [
                    {"type": "battery", "label": "V = 10V"},
                    {"type": "wire", "label": "conductor"},
                    {"type": "bulb", "label": "load"},
                ],
                "connections": [
                    {"from": "battery", "to": "wire"},
                    {"from": "wire", "to": "bulb"},
                    {"from": "bulb", "to": "battery"},
                ],
                "annotations": ["The battery supplies the potential difference"],
                "highlight": "battery",
            },
        },
    },
    {
        "id": "resistance",
        "priority": 1,
        "baseSeconds": 45,
        "query": "resistance resist conductor opposition flow charges",
        "objective": {
            "english": "Explain what resistance is",
            "hindi": "प्रतिरोध क्या है, यह समझाना",
            "hinglish": "Explain what resistance is",
        },
        "narration": {
            "english": (
                "And what is Resistance? It opposes the flow, like a speed "
                "breaker. More resistance means less current."
            ),
            "hindi": (
                "और प्रतिरोध क्या है? यह बहाव को रोकता है, जैसे स्पीड ब्रेकर। "
                "ज़्यादा प्रतिरोध यानी कम धारा।"
            ),
            "hinglish": (
                "Aur Resistance kya hai? Yeh flow ko rokata hai, jaise speed "
                "breaker. Zyada resistance matlab kam current."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "Resistance is measured in ohms and depends on the material.",
                "advanced": "R = rho x L / A, so length and cross-section change it directly.",
            },
            "hindi": {
                "intermediate": "प्रतिरोध ओम में मापा जाता है और पदार्थ पर निर्भर करता है।",
                "advanced": "R = rho x L / A, इसलिए लंबाई और अनुप्रस्थ काट इसे बदलते हैं।",
            },
            "hinglish": {
                "intermediate": "Resistance ohms mein measure hoti hai aur material par depend karti hai.",
                "advanced": "R = rho x L / A, toh length aur cross-section ise directly change karte hain.",
            },
        },
        "visual": {
            "type": "circuit",
            "data": {
                "components": [
                    {"type": "battery", "label": "V = 10V"},
                    {"type": "wire", "label": "conductor"},
                    {"type": "resistor", "label": "R = 5 ohm"},
                ],
                "connections": [
                    {"from": "battery", "to": "wire"},
                    {"from": "wire", "to": "resistor"},
                    {"from": "resistor", "to": "battery"},
                ],
                "annotations": ["The resistor opposes the flow of charge"],
                "highlight": "resistor",
            },
        },
    },
    {
        "id": "ohms-law",
        "priority": 0,
        "baseSeconds": 60,
        "query": "ohm law potential difference proportional current resistance formula",
        "objective": {
            "english": "Explain the V = IR relationship",
            "hindi": "V = IR संबंध को समझाना",
            "hinglish": "Explain the V=IR relationship",
        },
        "narration": {
            "english": (
                "Ohm's Law says V = I x R. That means Voltage equals Current "
                "times Resistance. To find I, we rearrange to I = V/R. If V is "
                "10 and R is 5, then I is 2 Amperes."
            ),
            "hindi": (
                "ओम का नियम कहता है कि V = I x R। यानी वोल्टेज बराबर धारा गुणा "
                "प्रतिरोध। I निकालना हो तो I = V/R होता है। मान लो V 10 है और R 5, "
                "तो I होगा 2 एम्पियर।"
            ),
            "hinglish": (
                "Ohm's Law kehta hai ki V = I x R. Iska matlab hai Voltage equals "
                "Current into Resistance. Agar I nikalna ho, toh I = V/R hota hai. "
                "Maan lo V 10 hai aur R 5, toh I hoga 2 Amperes."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "The V-I graph of an ohmic conductor is a straight line through the origin.",
                "advanced": "The law holds only at constant temperature; filaments and diodes are non-ohmic.",
            },
            "hindi": {
                "intermediate": "ओमीय चालक का V-I ग्राफ मूल बिंदु से गुजरती सीधी रेखा होता है।",
                "advanced": "यह नियम केवल स्थिर तापमान पर लागू होता है; फिलामेंट और डायोड अन-ओमीय हैं।",
            },
            "hinglish": {
                "intermediate": "Ohmic conductor ka V-I graph origin se guzarti straight line hoti hai.",
                "advanced": "Yeh law sirf constant temperature par valid hai; filament aur diode non-ohmic hain.",
            },
        },
        "visual": {
            "type": "equation",
            "data": {
                "steps": [
                    {"expression": "V = I x R", "label": "Ohm's Law"},
                    {"expression": "I = V / R", "label": "Solve for current"},
                    {"expression": "I = 10 / 5 = 2A", "label": "Substitute values"},
                ],
                "format": "katex",
                "highlight": "result",
            },
        },
    },
    {
        "id": "ohms-law-application",
        "priority": 0,
        "baseSeconds": 30,
        "checkpoint": True,
        "query": "resistance doubled current halved inverse relationship",
        "objective": {
            "english": "Test understanding of the current-resistance relationship",
            "hindi": "धारा और प्रतिरोध के संबंध की समझ जाँचना",
            "hinglish": "Test understanding of the relationship between current and resistance",
        },
        "narration": {
            "english": (
                "Now a question. If the voltage stays the same and we increase "
                "the resistance, what happens to the current?"
            ),
            "hindi": (
                "अब एक सवाल। अगर वोल्टेज वही रहे और हम प्रतिरोध बढ़ा दें, तो धारा "
                "का क्या होगा?"
            ),
            "hinglish": (
                "Ab ek sawal. Agar voltage same rahe, aur hum resistance badha "
                "dein, toh current ka kya hoga?"
            ),
        },
        "depth": {
            "english": {
                "intermediate": "Answer in one line and say why.",
                "advanced": "Justify your answer using the form of the equation.",
            },
            "hindi": {
                "intermediate": "एक पंक्ति में उत्तर दो और कारण बताओ।",
                "advanced": "समीकरण के रूप का उपयोग करके अपना उत्तर सिद्ध करो।",
            },
            "hinglish": {
                "intermediate": "Ek line mein answer do aur reason bhi batao.",
                "advanced": "Equation ke form se apna answer justify karo.",
            },
        },
        "visual": {
            "type": "graph",
            "data": {
                "xAxis": {"label": "Resistance (ohm)", "min": 1, "max": 20},
                "yAxis": {"label": "Current (A)", "min": 0, "max": 10},
                "series": [
                    {
                        "name": "I = V/R (V=10V)",
                        "points": [
                            {"x": 1, "y": 10.0},
                            {"x": 2, "y": 5.0},
                            {"x": 5, "y": 2.0},
                            {"x": 10, "y": 1.0},
                            {"x": 20, "y": 0.5},
                        ],
                        "type": "curve",
                    }
                ],
                "annotations": [],
                "title": "Current vs Resistance at constant Voltage",
            },
        },
    },
    {
        "id": "ohms-law-practice",
        "priority": 4,
        "baseSeconds": 60,
        "query": "ohm law formula current resistance calculation",
        "objective": {
            "english": "Practise rearranging and applying V = IR",
            "hindi": "V = IR को हल करने और लागू करने का अभ्यास",
            "hinglish": "Practise rearranging and applying V = IR",
        },
        "narration": {
            "english": (
                "Let's practise. If V is 12 volts and R is 4 ohms, then I is 3 "
                "amperes. Now double the resistance to 8 ohms and the current "
                "halves to 1.5 amperes."
            ),
            "hindi": (
                "अभ्यास करते हैं। अगर V 12 वोल्ट है और R 4 ओम, तो I होगा 3 एम्पियर। "
                "अब प्रतिरोध दोगुना करके 8 ओम करो, तो धारा आधी होकर 1.5 एम्पियर हो जाएगी।"
            ),
            "hinglish": (
                "Practice karte hain. Agar V 12 volts hai aur R 4 ohms, toh I hoga "
                "3 amperes. Ab resistance double karke 8 ohms karo, toh current "
                "aadha hokar 1.5 amperes ho jayega."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "Notice the current scales as the reciprocal of resistance.",
                "advanced": "Check that power P = I squared R falls even faster than current.",
            },
            "hindi": {
                "intermediate": "ध्यान दो कि धारा प्रतिरोध के व्युत्क्रम के अनुपात में बदलती है।",
                "advanced": "जाँचो कि शक्ति P = I वर्ग R धारा से भी तेज़ी से घटती है।",
            },
            "hinglish": {
                "intermediate": "Dhyan do ki current resistance ke reciprocal ke hisaab se change hoti hai.",
                "advanced": "Check karo ki power P = I square R current se bhi tezi se girti hai.",
            },
        },
        "visual": {
            "type": "equation",
            "data": {
                "steps": [
                    {"expression": "I = V / R", "label": "Start from Ohm's Law"},
                    {"expression": "I = 12 / 4 = 3A", "label": "First case"},
                    {"expression": "I = 12 / 8 = 1.5A", "label": "Resistance doubled"},
                ],
                "format": "katex",
                "highlight": "result",
            },
        },
    },
    {
        "id": "lesson-summary",
        "priority": 2,
        "baseSeconds": 30,
        "query": "summary ohm law revision recap",
        "objective": {
            "english": "Summary and next steps",
            "hindi": "सारांश और आगे के कदम",
            "hinglish": "Summary and next steps",
        },
        "narration": {
            "english": (
                "Great job! Today we learned how Current, Voltage and Resistance "
                "are connected through Ohm's law. Next class we will build "
                "circuits."
            ),
            "hindi": (
                "बहुत बढ़िया! आज हमने सीखा कि धारा, वोल्टेज और प्रतिरोध ओम के नियम से "
                "कैसे जुड़े हैं। अगली कक्षा में हम परिपथ बनाएँगे।"
            ),
            "hinglish": (
                "Great job! Aaj humne seekha ki Current, Voltage, aur Resistance "
                "kaise ek dusre se jude hue hain Ohm's law ke through. Agli class "
                "mein hum circuits banayenge."
            ),
        },
        "depth": {
            "english": {
                "intermediate": "Revise the units: volt, ampere and ohm.",
                "advanced": "Next we extend this to networks of resistors.",
            },
            "hindi": {
                "intermediate": "इकाइयाँ दोहराओ: वोल्ट, एम्पियर और ओम।",
                "advanced": "आगे हम इसे प्रतिरोधकों के नेटवर्क तक बढ़ाएँगे।",
            },
            "hinglish": {
                "intermediate": "Units revise karo: volt, ampere aur ohm.",
                "advanced": "Aage hum ise resistors ke networks tak extend karenge.",
            },
        },
        "visual": {
            "type": "concept_map",
            "data": {
                "nodes": [
                    {"id": "i", "label": "Current (I)", "type": "concept"},
                    {"id": "v", "label": "Voltage (V)", "type": "concept"},
                    {"id": "r", "label": "Resistance (R)", "type": "concept"},
                    {"id": "ohm", "label": "V = I x R", "type": "formula"},
                ],
                "edges": [
                    {"from": "ohm", "to": "v", "label": "defines"},
                    {"from": "ohm", "to": "i", "label": "defines"},
                    {"from": "ohm", "to": "r", "label": "opposes"},
                ],
                "layout": "hierarchical",
            },
        },
    },
]

CONCEPTS_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CONCEPTS}

# The concept the checkpoint assesses, used by evaluation and the report.
CHECKPOINT_CONCEPT_ID = "ohms-law"

NEXT_TOPIC = {"id": "series-parallel-circuits", "title": "Series and Parallel Circuits"}
