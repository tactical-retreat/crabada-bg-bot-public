from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dacite import from_dict

from common.faction import CrabClass


@dataclass()
class LoginInfo(object):
    """Info returned on login."""
    user_id: int  # 1234
    owner: str  # "0x243423423423423434343434",
    level: int  # 4
    # experience: int # 350
    # "user_address": "0x243423423423423434343434",
    # "owner_reward_percent": 100,
    # "email_address": "someguy@gmail.com",
    # "username": null,
    # "first_name": null,
    # "last_name": null,
    # "full_name": "Crabadian someguy",
    # "is_master_account": true,
    # "is_disabled": false,
    # "is_game_notify": false,
    # "is_deleted": false,
    # "is_battle_notify": true,
    crabada_slots: int  # 13
    # "photo": null,
    # next_experience: 500,
    # "crabadas": [{}]
    access_token: str
    refresh_token: str

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=LoginInfo, data=data)


@dataclass()
class RewardInfo(object):
    """Details about rewards in a mine."""
    node_id: int  # 5
    origin_item_id: int  # 2
    amount: float  # 3.75

    #     "percent": 0,
    #     "is_sure": true,
    #     "can_be_looted": true,
    #     "type": 9999,
    #     "stackable": true,
    #     "description": "Crabada Token",
    #     "user_id": 1234

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=RewardInfo, data=data)


@dataclass()
class MineInfo(object):
    """Details about a mine."""
    mine_id: int  # 512199
    node_id: int  # 5
    miner_id: int  # 1234
    start_time: int  # 1653389330
    end_time: int  # 1653393370
    # "crabada_id_1": 12345,
    # "crabada_id_2": 12346,
    # "crabada_id_3": 12347,
    # "position_1": 11,
    # "position_2": 12,
    # "position_3": 21,
    attack_time: int  # 0,
    looter_id: int  # 0
    # "loot_crabada_id_1": 0,
    # "loot_crabada_id_2": 0,
    # "loot_crabada_id_3": 0,
    winner_id: int  # 0
    status: int  # 1

    # "process": 1,
    # "is_looter_claim": false,
    # "game_record": null,
    rewards: list[RewardInfo]
    crabada_1_info: Optional[CrabadaData]
    crabada_2_info: Optional[CrabadaData]
    crabada_3_info: Optional[CrabadaData]

    def is_complete(self) -> bool:
        return time.time() > self.end_time

    def can_looter_claim(self) -> bool:
        # Tiny bit of padding here.
        return time.time() > self.attack_time + 31 * 60

    def amount_for_mat(self, item_id: int) -> float:
        for item in self.rewards:
            if item.origin_item_id == item_id:
                return item.amount
        return 0.0

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=MineInfo, data=data)


@dataclass()
class EnergyInfo(object):
    """Energy for the crabada and reset time."""
    energy: int  # 0-24
    reset_time: int  # 1653696000

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=EnergyInfo, data=data)


@dataclass()
class CrabadaData(object):
    """Details about an individual crabada."""
    crabada_id: int  # 12345
    # id: int  # 45678
    # user_id: int  # 3456
    # name: int  # "Crabada 12345"
    # description: int  # null
    crabada_class: int  # 3
    # class_name: int  # "PRIME"
    # experience: int  # 0
    # is_origin: int  # 0
    # is_genesis: int  # 0
    # legend_number: int  # 0
    # pure_number: int  # 6
    # parts: int  # [31, 37, 32, 35, 35, 37]
    # shell_id: int  # 31
    # horn_id: int  # 37
    # body_id: int  # 32
    # mouth_id: int  # 35
    # eyes_id: int  # 35
    # pincers_id: int  # 37
    # hp: int  # 3000
    # speed: int  # 38
    # damage: int  # 852
    # critical: int  # 16
    # armor: int  # 68
    level: int  # 3 - never seems to change vs real_level
    real_level: int  # 3 - never seems to change vs level
    # eat_time: int  # 1652473630
    power_level: int  # 6 - current hunger
    # pincers_skill: int  # "IRON_MAN"
    # pincers_skill_name: int  # "AvaBeam"
    # pincers_percent: int  # 240
    # pincers_turn: int  # 1
    # pincers_skill_description: int  # "long description"
    # eyes_effect: int  # "WEAKEN"
    # eyes_effect_name: int  # "Weaken"
    # eyes_effect_percent: int  # 25
    # eyes_effect_turn: int  # 1
    # eyes_effect_chance: int  # 10
    # eyes_effect_description: int  # "long description"
    # max_hp: int  # 3075
    # max_damage: int  # 877
    # max_armor: int  # 70
    # max_speed: int  # 38
    # max_critical: int  # 16
    max_power_level: int  # 30 - max hunger
    combat_power: int  # 4961
    energy: EnergyInfo

    @property
    def effective_level(self) -> int:
        """Calculate the actual level of the crab based on hunger and max level."""
        ratio = self.power_level / self.max_power_level
        return max(int(math.ceil(ratio * self.max_level)), 1)

    @property
    def max_level(self) -> int:
        # Not clear why these are always the same, but compensate in case that changes.
        return max(self.level, self.real_level)

    def class_enum(self):
        return CrabClass(self.crabada_class)

    def is_tank(self):
        return self.class_enum() in [CrabClass.BULK, CrabClass.SURGE, CrabClass.GEM]

    def is_dps(self):
        return self.class_enum() in [CrabClass.PRIME, CrabClass.CRABOID, CrabClass.RUINED]

    def is_sup(self):
        return self.class_enum() in [CrabClass.SUNKEN, CrabClass.ORGANIC]

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=CrabadaData, data=data)


@dataclass()
class MoneyItem(object):
    """TUS/CRA/SHELL/CRAM descriptors."""
    TUS_ID = 1
    CRA_ID = 2
    SHELL_ID = 3
    CRAM_ID = 5

    origin_item_id: int  # 1
    amount: float  # 1027
    user_id: int  # 1234
    item_name: str  # "TUS" "CRA" "Crystal Shell" "CRAM"

    # item_description: "Treasure Under Sea Token"

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=MoneyItem, data=data)


class MoneySummary(object):
    """Given a list of Money, counts specific interesting items."""

    def __init__(self, items: list[MoneyItem]):
        data = {i.origin_item_id: i.amount for i in items}
        self.tus = data.get(MoneyItem.TUS_ID, 0) or 0
        self.cra = data.get(MoneyItem.CRA_ID, 0) or 0
        self.shells = data.get(MoneyItem.SHELL_ID, 0) or 0
        self.cram = data.get(MoneyItem.CRAM_ID, 0) or 0


@dataclass()
class InventoryItem(object):
    """Stuff in inventory, materials, food, etc."""
    FLAG_ID = 101001
    FLORAL_ID = 101002
    CORAL_ID = 101003
    OCTO_ID = 101004
    TENTACRA_ID = 101005
    SANDWICH_ID = 201001

    origin_item_id: int  # 101002
    amount: int  # 183
    item_name: str  # "Purple Floral"
    item_description: str  # "A level 1 material used to exchange TUS, craft equipment or food"
    level: int  # 1
    experience: int  # 0
    durability: int  # 100

    # "main_hp_point": 0,
    # "main_speed_point": 0,
    # "main_damage_point": 0,
    # "main_critical_point": 0,
    # "main_armor_point": 0,
    # "main_hp_percent": 0,
    # "main_speed_percent": 0,
    # "main_damage_percent": 0,
    # "main_critical_percent": 0,
    # "main_armor_percent": 0,
    # "sub_hp_point": 0,
    # "sub_speed_point": 0,
    # "sub_damage_point": 0,
    # "sub_critical_point": 0,
    # "sub_armor_point": 0,
    # "sub_hp_percent": 0,
    # "sub_speed_percent": 0,
    # "sub_damage_percent": 0,
    # "sub_critical_percent": 0,
    # "sub_armor_percent": 0

    # item_description: "Treasure Under Sea Token"

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=InventoryItem, data=data)


class InventorySummary(object):
    """Given a list of inventory, counts specific interesting materials and food."""

    def __init__(self, items: list[InventoryItem]):
        data = {i.origin_item_id: i.amount for i in items}
        self.flag_count = data.get(InventoryItem.FLAG_ID, 0)
        self.floral_count = data.get(InventoryItem.FLORAL_ID, 0)
        self.coral_count = data.get(InventoryItem.CORAL_ID, 0)
        self.octo_count = data.get(InventoryItem.OCTO_ID, 0)
        self.tentacra_count = data.get(InventoryItem.TENTACRA_ID, 0)
        self.sandwich_count = data.get(InventoryItem.SANDWICH_ID, 0)

    def convert_available(self):
        """If true we can do a conversion to food/tus."""
        return min([self.flag_count, self.floral_count, self.coral_count, self.octo_count, self.tentacra_count])

    def rarest_mat(self) -> int:
        mats_and_counts = [
            (self.flag_count, InventoryItem.FLAG_ID),
            (self.floral_count, InventoryItem.FLORAL_ID),
            (self.coral_count, InventoryItem.CORAL_ID),
            (self.octo_count, InventoryItem.OCTO_ID),
            (self.tentacra_count, InventoryItem.TENTACRA_ID),
        ]
        mats_and_counts.sort(key=lambda x: x[0])
        print(mats_and_counts)
        print('picking', mats_and_counts[0][1])
        return mats_and_counts[0][1]


@dataclass()
class MineZoneInfo(object):
    """Details about a mine zone."""
    node_id: int  # 5,
    # campaign_id: int # 1,
    # index_number: int # 5,
    # name: str # "Treasure Isle 1",
    # description: Op null,
    # reward_random": 0,
    is_mine_zone: bool  # true,
    # is_final": false,
    # "photo": null,
    # "rewards": [{}]
    # "bots": [{}]
    # "mine_rewards": [{}]
    # "max_remaining_energy": 7951,
    # "max_energy_user_can_play": 9360,
    # "star": "2"
    passed: bool  # true,
    can_attack: bool  # true,

    def is_attackable_mine_zone(self) -> bool:
        """True if we can mine there (node 5/10/etc) and we've beaten it."""
        return self.is_mine_zone and self.passed and self.can_attack

    @staticmethod
    def convert(data: Dict[str, Any]):
        return from_dict(data_class=MineZoneInfo, data=data)
