"""Paired endings (Game8 "All Paired Endings", archives/628208, a work-in-progress page, read 2026-10-31).

A pair gets an ending if they unlock and watch their A support and share the most
support points with each other. Eshmel instead picks, after the final battle, one
partner among units at Support Level 5. The bool marks endings whose text is
romantic (marriage, proposal, children); others are platonic or vague.
No S supports, marriage system or child units exist (Game8 "Is There Romance?").
"""

ENDINGS = [
    ("Bonaventure", "Lilian", True),
    ("Buccar", "Ludia", False),
    ("Buccar", "Olympia", False),
    ("Cai", "Theodora", True),
    ("Cai", "Tialla", True),
    ("Dante", "Goliath", True),
    ("Dante", "Jester", False),
    ("Diego", "Esmeralda", False),
    ("Diego", "Ninae", False),
    ("Dietrich", "Esmeralda", True),
    ("Dietrich", "Fabio", False),
    ("Dietrich", "Mikaela", False),
    ("Esmeralda", "Fabio", False),
    ("Fabio", "Mikaela", False),
    ("Fianna", "Simon", True),
    ("Goliath", "Loretta", False),
    ("Goliath", "Ultand", True),
    ("Halvin", "Jester", False),
    ("Leda", "Mu", False),
    ("Leda", "Olympia", False),
    ("Leda", "Sirocco", False),
    ("Lilian", "Lysander", True),
    ("Lilian", "Tobias", True),
    ("Loretta", "Seteth", False),
    ("Ludia", "Simon", True),
    ("Mikaela", "Simon", False),
    ("Mu", "Peter", True),
    ("Mu", "Sirocco", True),
    ("Sha Lan", "Sirocco", True),
    ("Simon", "Ursula", True),
    ("Alexandra", "Eshmel", True),
    ("Benditz", "Eshmel", False),
    ("Bonaventure", "Eshmel", False),
    ("Buccar", "Eshmel", False),
    ("Cai", "Eshmel", False),
    ("Catania", "Eshmel", False),
    ("Dadao", "Eshmel", False),
    ("Dante", "Eshmel", False),
    ("Diego", "Eshmel", False),
    ("Dietrich", "Eshmel", False),
    ("Eshmel", "Esmeralda", False),
    ("Eshmel", "Fabio", False),
    ("Eshmel", "Fianna", False),
    ("Eshmel", "Gaitz", False),
    ("Eshmel", "Goliath", False),
    ("Eshmel", "Guzran", False),
    ("Eshmel", "Halvin", False),
    ("Eshmel", "Hong Hua", False),
    ("Eshmel", "Inyoni", True),
    ("Eshmel", "Io", False),
    ("Eshmel", "Jasmine", False),
    ("Eshmel", "Jester", False),
    ("Eshmel", "Leda", False),
    ("Eshmel", "Lilian", False),
    ("Eshmel", "Loretta", True),
    ("Eshmel", "Ludia", False),
    ("Eshmel", "Lysander", False),
    ("Eshmel", "Majide", False),
    ("Eshmel", "Mikaela", False),
    ("Eshmel", "Mu", False),
    ("Eshmel", "Nezha", False),
    ("Eshmel", "Ninae", False),
    ("Eshmel", "Noctula", False),
    ("Eshmel", "Nydine", False),
    ("Eshmel", "Olympia", False),
    ("Eshmel", "Peppe", False),
    ("Eshmel", "Peter", False),
    ("Eshmel", "Sha Lan", False),
    ("Eshmel", "Simon", False),
    ("Eshmel", "Sirocco", False),
    ("Eshmel", "Sofia", False),
    ("Eshmel", "Theodora", False),
    ("Eshmel", "Tialla", False),
    ("Eshmel", "Tobias", False),
    ("Eshmel", "Ultand", False),
    ("Eshmel", "Ursula", False),
    ("Eshmel", "Yang Jie", False),
    ("Eshmel", "Zarcone", False),
]

# Short favourite-gift line per unit for tables: Loved gifts, else the start of Really Liked.
from gifts import GIFT_PREFS  # noqa: E402

GIFTS = {u: (d["loved"] or ("RL: " + ", ".join(d["liked"].split(", ")[:5]) if d["liked"] else ""))
         for u, d in GIFT_PREFS.items() if d["loved"] or d["liked"]}


# Small tie-breaks on top of the squad/path score.
PREFER = {
    ("Eshmel", "Hong Hua"): 0.25,  # story companions; players report this (platonic) ending
}
