from __future__ import annotations

from collections import Counter
from enum import auto, IntEnum


class CrabClass(IntEnum):
    SURGE = 1
    SUNKEN = 2
    PRIME = 3
    BULK = 4
    CRABOID = 5
    RUINED = 6
    GEM = 7
    ORGANIC = 8

    def faction(self):
        return CLASS_TO_FACTION[self]


class Faction(IntEnum):
    ABYSS = auto()  # Ruined
    TRENCH = auto()  # Sunken
    ORE = auto()  # Surge & Bulk
    LUX = auto()  # Prime & Gem
    MACHINE = auto()  # Craboid
    FAERIE = auto()  # Organic

    def is_advantaged_over(self, other):
        return other in ADVANTAGE_MAP[self]

    @staticmethod
    def faction_for(c1: CrabClass, c2: CrabClass, c3: CrabClass):
        freq = Counter([c1.faction(), c2.faction(), c3.faction()]).most_common()
        if freq[0][1] >= 2:
            return freq[0][0]
        return None

    def image(self) -> str:
        return ICON_MAP[self]

    @staticmethod
    def image_for(attacker: Faction, defender: Faction) -> str:
        return ICON_MAP[defender]


CLASS_TO_FACTION = {
    CrabClass.SURGE: Faction.ORE,
    CrabClass.SUNKEN: Faction.TRENCH,
    CrabClass.PRIME: Faction.LUX,
    CrabClass.BULK: Faction.ORE,
    CrabClass.CRABOID: Faction.MACHINE,
    CrabClass.RUINED: Faction.ABYSS,
    CrabClass.GEM: Faction.LUX,
    CrabClass.ORGANIC: Faction.FAERIE
}

ADVANTAGE_MAP = {
    Faction.ABYSS: [Faction.MACHINE, Faction.TRENCH],
    Faction.TRENCH: [Faction.LUX, Faction.MACHINE],
    Faction.LUX: [Faction.ORE, Faction.FAERIE],
    Faction.ORE: [Faction.ABYSS, Faction.TRENCH],
    Faction.MACHINE: [Faction.FAERIE, Faction.LUX],
    Faction.FAERIE: [Faction.ABYSS, Faction.ORE],
}

NO_FACTION_ICON = 'https://storage.googleapis.com/tr-crabada-bot-data/none.png'

ICON_MAP = {
    Faction.ABYSS: 'https://storage.googleapis.com/tr-crabada-bot-data/abyss.png',
    Faction.TRENCH: 'https://storage.googleapis.com/tr-crabada-bot-data/trench.png',
    Faction.LUX: 'https://storage.googleapis.com/tr-crabada-bot-data/lux.png',
    Faction.ORE: 'https://storage.googleapis.com/tr-crabada-bot-data/ore.png',
    Faction.MACHINE: 'https://storage.googleapis.com/tr-crabada-bot-data/machine.png',
    Faction.FAERIE: 'https://storage.googleapis.com/tr-crabada-bot-data/faerie.png',
}
