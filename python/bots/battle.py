import asyncio
import random
import traceback
from datetime import datetime
from typing import Tuple

from battle_client.client import BattleClient
from battle_client.types import MineInfo, InventorySummary, CrabadaData, InventoryItem
from common.config_local import DEFAULT_CONFIG
from common.cooldown import CooldownManager
from common.discord import AlertManager


class BattleManager(object):
    """Bot class that manages the BattleGame interactions."""

    def __init__(self):
        # Configuration for the bot.
        self.config = DEFAULT_CONFIG
        # API Client.
        self.battle_client = BattleClient()

        # Discord alert posting.
        self.alert_manager = AlertManager()
        # How frequently we will cycle through actions.
        self.poll_interval = self.config.battle_poll_interval

        # Amount of time between any action executed.
        self.action_cd = CooldownManager('execute_action', 5)
        # Minimum amount of time between attempting to loot.
        self.loot_action_cd = CooldownManager('loot_action', 90)

    async def mine_loop(self):
        print('Game loop starting')

        # Bot is starting up so post a notification to Discord.
        # Include details about money because why not.
        money = self.battle_client.money()
        content = 'Money in account'
        for m in money:
            content += f'\n  {m.item_name}: {m.amount}'
        self.alert_manager.simple_embed('Bot Starting', content)

        # Primary action/sleep loop, capturing all exceptions and alerting on them.
        while True:
            try:
                await self.do_action_loop()
            except Exception as ex:
                print(traceback.format_exc())
                self.alert_manager.error(str(ex))

            await asyncio.sleep(self.poll_interval)

    async def do_action_loop(self):
        """Do stuff every period.

        In order, if we need to:
        1) Close mines
        2) Close loots
        3) Acquire food (maintain one per crab)
        4) Use excess mats for TUS
        5) Loot one time
        6) Open as many mines as necessary
        """
        print('Looping through actions')

        # Since there is a delay between actions, additional mines / loots might
        # need to closed by the time we're done closing the first batch. So do it
        # in a loop until we stop doing stuff.
        did_close_mines = True
        while did_close_mines:
            did_close_mines = await self.try_closing_mines()

        did_close_loots = True
        while did_close_loots:
            did_close_loots = await self.try_closing_loots()

        # Get food if necessary. Return the resulting inventory and check if we can make TUS.
        inventory_summary = await self.try_acquire_food()
        await self.try_acquire_tus(inventory_summary)

        # if self.config.battle_auto_level:
        #     await self.try_level_crabs()

        # Check what crabs are ready to be used, see if they need to be fed and feed em.
        available_crabs = self.battle_client.list_available_crabs()
        available_crabs = await self.try_feed_crabs(available_crabs, inventory_summary)

        # Figure out what mining zones have been cleared.
        mine_zones = self.battle_client.list_mine_zones()
        attackable_node_ids = [mz.node_id for mz in mine_zones if mz.is_attackable_mine_zone()]
        if not attackable_node_ids:
            # Some people are too dumb to complete adventure mode before starting the bot.
            self.alert_manager.simple_embed('Mining not available',
                                            'No zones available to attack; complete adventure mode')
            return

        # loot_crabs = []
        # if is_in_loot_window():
        #     # The first N hours of the day are dedicated to looting.
        #     # If we're in that window, try and loot with whatever we can.
        #     # If we're past that window those crabs get sent to mine.
        #     min_looter_level = self.config.battle_minimum_looter_level
        #     loot_crabs = [c for c in available_crabs if c.effective_level >= min_looter_level]
        #     available_crabs = [c for c in available_crabs if c.effective_level < min_looter_level]

        # Mining node is hardcoded to 5; let the noobs there loot and fail.
        # Higher nodes are likely to have actual players.
        await self.try_open_mines(5, available_crabs)
        # await self.try_loot(attackable_node_ids, loot_crabs, inventory_summary)
        #
        # if self.withdraw_cd.check_date():
        #     await self.do_withdraw()
        #
        # if self.bridge_cd.check_date():
        #     await self.do_bridge()
        #
        # if self.swap_cd.check_date():
        #     await self.do_swap()

    async def try_closing_mines(self) -> bool:
        """Attempt to close mines, returning True if any mine was closed."""
        print('Checking if mines need to be closed')
        did_close_mines = False
        open_mines = self.battle_client.list_my_open_mines(0)
        for mine in open_mines:
            if mine.is_complete():
                did_close_mines = True
                await self.claim_mine(mine)
                await asyncio.sleep(5)
        return did_close_mines

    async def try_closing_loots(self) -> bool:
        """Attempt to close loots, returning True if any loot was closed."""
        print('Checking if loots need to be closed')
        did_close_loots = False
        open_loots = self.battle_client.list_my_open_loots(0)
        for loot in open_loots:
            if loot.can_looter_claim():
                did_close_loots = True
                await self.claim_loot(loot)
                await asyncio.sleep(5)
        return did_close_loots

    async def try_acquire_food(self) -> InventorySummary:
        """Attempt to ensure we have at least 1 food per crab."""
        all_crabs = self.battle_client.sync()
        inventory_summary = InventorySummary(self.battle_client.inventory())
        if inventory_summary.sandwich_count >= len(all_crabs):
            print(f'Food level is sufficient: {inventory_summary.sandwich_count}')
            return inventory_summary
        want_food = len(all_crabs) - inventory_summary.sandwich_count
        if not inventory_summary.convert_available():
            print(f'Food level is deficient but unable to convert, wanted to make: {want_food}')
            return inventory_summary

        request_food = min(want_food, inventory_summary.convert_available())
        await self.craft_food(request_food)
        await asyncio.sleep(5)
        inventory_summary = InventorySummary(self.battle_client.inventory())
        await asyncio.sleep(1)
        return inventory_summary

    async def try_acquire_tus(self, inventory_summary: InventorySummary):
        if not inventory_summary.convert_available():
            print('Insufficient materials to craft tus')
            return
        await self.craft_tus(inventory_summary.convert_available())
        await asyncio.sleep(5)

    async def try_feed_crabs(self,
                             available_crabs: list[CrabadaData],
                             inventory_summary: InventorySummary) -> list[CrabadaData]:
        crabs_to_feed = [c for c in available_crabs if c.power_level < 2 or c.effective_level < c.max_level]
        if not crabs_to_feed:
            print('No crabs need to be fed')
            return available_crabs

        if inventory_summary.sandwich_count:
            await self.feed_crabs(crabs_to_feed)
            await asyncio.sleep(5)
            available_crabs = self.battle_client.list_available_crabs()
            await asyncio.sleep(1)

        return available_crabs

    async def try_open_mines(self, attack_node: int, available_crabs: list[CrabadaData]):
        available_crabs = [c for c in available_crabs if c.power_level >= 2 and c.energy.energy >= 4]
        if len(available_crabs) < 3:
            print('Not enough crabs to mine')
            return

        random.shuffle(available_crabs)
        tank = [c for c in available_crabs if c.is_tank()]
        dps = [c for c in available_crabs if c.is_dps()]
        sup = [c for c in available_crabs if c.is_sup()]

        print(f'Trying to open {len(available_crabs) // 3} mines in {attack_node}'
              f' using {len(tank)} tank {len(dps)} dps {len(sup)} sup')
        while len(tank) + len(dps) + len(sup) > 2:
            crab1, crab1p, crab2, crab2p, crab3, crab3p = assemble_team(tank, dps, sup)
            await self.start_mine(attack_node, crab1, crab1p, crab2, crab2p, crab3, crab3p)
            await asyncio.sleep(5)

    async def claim_mine(self, mine: MineInfo):
        print(f'Trying to claim mine {mine.mine_id} in node {mine.node_id}')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Claim Mine', -1, mine.mine_id)
        self.battle_client.claim_mine(mine.mine_id)
        if mine.winner_id == mine.miner_id:
            result_text = 'You won!'
            icon = 'https://i.imgur.com/TPFdwZG.png'
        else:
            result_text = 'You lost.'
            icon = 'https://i.imgur.com/LON2Wdj.png'
        self.alert_manager.ok(result_text, icon=icon)

    async def claim_loot(self, loot: MineInfo):
        print(f'Trying to claim loot {loot.mine_id} in node {loot.node_id}')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Claim Loot', -1, loot.mine_id)
        self.battle_client.claim_loot(loot.mine_id)
        self.alert_manager.ok('Done')

    async def start_mine(self,
                         node_id: int,
                         crab1: CrabadaData, crab1p: str,
                         crab2: CrabadaData, crab2p: str,
                         crab3: CrabadaData, crab3p: str):
        print(f'Starting mine with {crab1.crabada_id} / {crab2.crabada_id} / {crab3.crabada_id}')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Start Mine', -1)
        self.battle_client.start_mine(node_id,
                                      crab1.crabada_id, crab1p,
                                      crab2.crabada_id, crab2p,
                                      crab3.crabada_id, crab3p)
        content = f'Started mine in node {node_id} using:'
        content += f'\n  {crab1.class_enum().name}({crab1.effective_level}) in {fix_pos(crab1p)}'
        content += f'\n  {crab2.class_enum().name}({crab2.effective_level}) in {fix_pos(crab2p)}'
        content += f'\n  {crab3.class_enum().name}({crab3.effective_level}) in {fix_pos(crab3p)}'
        self.alert_manager.ok(content)

    async def craft_food(self, amount: int):
        print(f'Crafting {amount} sandwiches')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Craft Food', -1)
        self.battle_client.craft_lv1_food(amount)
        self.alert_manager.ok(f'Crafted {amount} sandwiches')

    async def craft_tus(self, amount: int):
        print(f'Crafting {amount} TUS')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Craft Tus', -1)
        self.battle_client.craft_lv1_tus(amount)
        self.alert_manager.ok(f'Crafted {amount * 51} tus')

    async def feed_crabs(self, crabs_to_feed: list[CrabadaData]):
        print(f'Feeding {len(crabs_to_feed)} crabs')
        if not self.action_cd.check_cooldown(0):
            return
        self.alert_manager.start_action('Feed Crabs', -1)
        for crab in crabs_to_feed:
            self.battle_client.feed_crab(crab.crabada_id, InventoryItem.SANDWICH_ID)
            await asyncio.sleep(2)
        self.alert_manager.ok(f'Fed {len(crabs_to_feed)} crabs')


def from_in_order(a1: list, a2: list, a3: list):
    """Pop the first item off any list with items."""
    if a1:
        return a1.pop()
    if a2:
        return a2.pop()
    return a3.pop()


def fix_pos(pos: str) -> str:
    """Convert a position string to something more readable."""
    col = {'1': 'F', '2': 'B'}[pos[0]]
    row = {'1': 'T', '2': 'M', '3': 'B'}[pos[1]]
    return col + row


def is_in_loot_window() -> bool:
    """If true, try to loot with any looting crabs.

    It takes 6 hours to mine out energy. Add two hours for buffer.
    So the first 16 hours of the day are for looting, and the last 8 are for mining.
    """
    return datetime.utcnow().hour < 17


def assemble_team(tank: list[CrabadaData], dps: list[CrabadaData], sup: list[CrabadaData]) -> Tuple[
    CrabadaData, str, CrabadaData, str, CrabadaData, str]:
    """Do a mediocre job of assembling a reasonable looking team.

    Assumes we have at least 3 crabs among all 3 lists of crab types.
    Obviously does not take anything interesting about the opposing crabs into account.
    """
    # Always prefer to have a tank in the upper right, but fall back to whatever
    crab1 = from_in_order(tank, sup, dps)
    crab1p = '11'

    # If we have an excess of tank / support compared to dps
    if len(tank) + len(sup) > len(dps):
        # Pick whichever type we have more of and put it in the middle right
        bigger = tank if len(tank) > len(sup) else sup
        crab2 = bigger.pop()
        crab2p = '12'
    else:
        # We have too much dps, so stick them in the back middle
        crab2 = dps.pop()
        crab2p = '22'

    # We want to prefer a dps for top left
    if dps:
        crab3 = dps.pop()
        crab3p = '21'
    else:
        # But if we don't have dps put anything in
        crab3 = from_in_order(tank, sup, [])
        crab3p = '13'

    return crab1, crab1p, crab2, crab2p, crab3, crab3p


def score_team(crabs: list[CrabadaData], bad_comp_penalty: int) -> int:
    """Score is the sum of the effective level, penalized if the team doesn't seem reasonable.

    The penalty is not hardcoded because we want to penalize our own crabs harder than
    opposing ones.
    """
    score = sum([c.effective_level for c in crabs])
    balanced = any([c.is_dps() for c in crabs]) and any([c.is_tank() for c in crabs])
    if not balanced:
        score -= bad_comp_penalty
    return score
