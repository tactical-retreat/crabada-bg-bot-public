import json
from typing import Any, Union

import requests

from battle_client.encryption import crabada_checksum
from battle_client.types import LoginInfo, MineInfo, CrabadaData, MoneyItem, InventoryItem, MineZoneInfo

# Headers that should be passed on every request.
# Authz is per account but should always be provided.
# Hash should only be provided on mutations.
DEFAULT_HEADERS = {
    'Host': 'battle-system-api.crabada.com',
    'User-Agent': 'UnityPlayer/2020.3.31f1 (UnityWebRequest/1.0, libcurl/7.80.0-DEV)',
    'Accept': '*/*',
    # 'Authorization': 'Bearer <token>',
    # 'Hash': 'C215ABE0934A2A42CFD4CC9423E101DA',
    'X-Unity-Version': '2020.3.31f1',
}


class BattleClient:
    """HTTP client for Crabada battle game."""

    # All battle api requests go here.
    BATTLE_URL = 'https://battle-system-api.crabada.com'

    def __init__(self, expect_keys=True):
        # Required for all requests
        self.access_token = ''
        # Currently unused. Haven't seen the BG refresh a token.
        self.refresh_token = ''
        # Generally we have keys unless we're going to sign in for the first time.
        if expect_keys:
            with open('battle_keys.json', 'r') as f:
                keys = json.load(f)
            self.access_token = keys['access_token']
            self.refresh_token = keys['refresh_token']

    def get_login_code(self, email_address: str) -> dict[str, Any]:
        """Request that a login code be sent to the email."""
        url = BattleClient.BATTLE_URL + '/crabada-user/public/sub-user/get-login-code'
        params = {'email_address': email_address}
        return self.api_request(url, params=params, auth=False)

    def login(self, email_address: str, code: str) -> LoginInfo:
        """Login with email/code and get back the auth tokens."""
        url = BattleClient.BATTLE_URL + '/crabada-user/public/sub-user/login'
        params = {
            'email_address': email_address,
            'code': code,
        }
        return LoginInfo.convert(self.api_post(url, json_data=params, auth=False))

    def list_my_open_mines(self, node_id: int) -> list[MineInfo]:
        """Get a list of mines opened. Probably no reason not to use 0 here."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/mine-zones/mine/open/miner'
        params = {
            # 0 gets results for all nodes
            # 5 is the lowest viable node
            'node_id': node_id,
        }
        return convert_list(MineInfo.convert, self.api_request_list(url, params))

    def list_my_open_loots(self, node_id: int) -> list[MineInfo]:
        """Get a list of loots opened. Probably no reason not to use 0 here."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/mine-zones/mine/active/looting'
        params = {'node_id': node_id}
        return convert_list(MineInfo.convert, self.api_request_list(url, params))

    def list_available_crabs(self) -> list[CrabadaData]:
        """This will list crabs that can be used for mining/looting.

        I thought it only returns viable crabs (fed/energy) but maybe not?
        Apparently also returns crabs that are still in a mine/loot if finished but not claimed.
        Called whenever you are prompted to pick crabs for a loot/mine.
        """
        url = BattleClient.BATTLE_URL + '/crabada-user/private/crabada/mine'
        return convert_list(CrabadaData.convert, self.api_request_list(url, {}))

    def money(self) -> list[MoneyItem]:
        """Details about tus/cra/shell balances"""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/money/info'
        return convert_list(MoneyItem.convert, self.api_request_list(url, {}))

    def inventory(self) -> list[InventoryItem]:
        """Details about materials and food. Pack into an InventorySummary for convenience."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/inventory/info'
        return convert_list(InventoryItem.convert, self.api_request_list(url, {}))

    def sync(self) -> list[CrabadaData]:
        """Returns details about all crabs.

        This is called whenever you go into the crabada view that lets you feed/level crabs.
        """
        url = BattleClient.BATTLE_URL + '/crabada-user/private/sync'
        return convert_list(CrabadaData.convert, self.api_request_list(url, {}))

    def list_mine_zones(self) -> list[MineZoneInfo]:
        """Returns all mining zones, useful for determining what nodes you have access to.

        Called whenever you go into the mine/loot page.
        """
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/all/mine-zones'
        return convert_list(MineZoneInfo.convert, self.api_request_list(url, {}))

    def start_mine(self, node_id: int,
                   crab1: int, crab1p: str,
                   crab2: int, crab2p: str,
                   crab3: int, crab3p: str) -> MineInfo:
        """Start a mine in a node with the given crabs and their position.

        Positions values are 1/2 (front/back) and 1/2/3 (top/middle/bottom), e.g.:
          21: rear top
          13: front bottom
        """
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/mine-zones/mine/create'
        params = {
            'node_id': node_id,
            'crabada_id_1': crab1,
            'crabada_id_2': crab2,
            'crabada_id_3': crab3,
            'p1': crab1p,
            'p2': crab2p,
            'p3': crab3p,
        }
        return MineInfo.convert(self.api_post(url, json_data=params))

    def claim_mine(self, mine_id: int) -> dict[str, Any]:
        """Claim a mine. Think the return type is a MineInfo."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/mine-zones/mine/claim'
        params = {'mine_id': mine_id}
        return self.api_post(url, json_data=params)

    def claim_loot(self, mine_id: int) -> dict[str, Any]:
        """Claim a loot. Think the return type is a MineInfo."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/campaign/mine-zones/mine/looter-claim'
        params = {'mine_id': mine_id}
        return self.api_post(url, json_data=params)

    def feed_crab(self, crabada_id: int, food_id: int) -> dict[str, Any]:
        """Feed a crab. Think the return type is a CrabadaInfo."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/crabada/eat'
        params = {
            'crabada_id': crabada_id,
            'food_id': food_id,
        }
        return self.api_post(url, json_data=params)

    def craft_lv1_food(self, amount: int):
        """Craft a sandwich.

        There are other kinds of food that can be crafted but I'm only implementing this one.
        All mining/looting happens in zone 1 / node 5 generally anyway.
        """
        url = BattleClient.BATTLE_URL + '/crabada-user/private/crafting/money-food'
        params = {
            'recipe_id': 6,
            'output_id': InventoryItem.SANDWICH_ID,
            'amount': amount,
            'material_1_id': InventoryItem.FLAG_ID,
            'material_1_amount': amount,
            'material_2_id': InventoryItem.FLORAL_ID,
            'material_2_amount': amount,
            'material_3_id': InventoryItem.CORAL_ID,
            'material_3_amount': amount,
            'material_4_id': InventoryItem.OCTO_ID,
            'material_4_amount': amount,
            'material_5_id': InventoryItem.TENTACRA_ID,
            'material_5_amount': amount,
        }
        return self.api_post(url, json_data=params)

    def craft_lv1_tus(self, amount: int):
        """Craft TUS from the level 1 ingredients."""
        url = BattleClient.BATTLE_URL + '/crabada-user/private/crafting/money-food'
        params = {
            'recipe_id': 1,
            'output_id': 1,
            'amount': amount,
            'material_1_id': InventoryItem.FLAG_ID,
            'material_1_amount': amount,
            'material_2_id': InventoryItem.FLORAL_ID,
            'material_2_amount': amount,
            'material_3_id': InventoryItem.CORAL_ID,
            'material_3_amount': amount,
            'material_4_id': InventoryItem.OCTO_ID,
            'material_4_amount': amount,
            'material_5_id': InventoryItem.TENTACRA_ID,
            'material_5_amount': amount,
        }
        return self.api_post(url, json_data=params)

    def api_post(self, url: str, json_data: dict, auth: bool = True) -> dict[str, Any]:
        """Mutating requests use this."""
        # Needs auth for everything except login
        return self._api_request(url, json_data, auth=auth, checksum=True, request_type='POST')

    def api_request(self, url: str, params: dict, auth: bool = True) -> dict[str, Any]:
        """Non-mutating requests for a single item use this."""
        return self._api_request(url, params, auth=auth)

    def api_request_list(self, url: str, params: dict, auth: bool = True) -> list[dict[str, Any]]:
        """Non-mutating requests for a list of items use this."""
        return self._api_request(url, params, auth=auth)

    def _api_request(self, url: str, params: dict, auth: bool = True, checksum: bool = False,
                     request_type: str = 'GET') -> Union[list[dict[str, Any]], dict[str, Any]]:
        """Send a Battle Game API Request.

        Always uses the standard headers.
        Generally sets the auth header (except for login requests).
        Sets the hash header on mutations.
        """
        final_headers = DEFAULT_HEADERS.copy()
        if auth:
            if not self.access_token:
                raise Exception('Attempted to make an authorized request before authz was set up')
            final_headers['Authorization'] = f'Bearer {self.access_token}'

        if request_type == 'GET':
            resp = requests.request(request_type, url, params=params, headers=final_headers, timeout=8).json()
        elif request_type == 'POST' and checksum:
            data = json.dumps(params, separators=(',', ':'))
            final_headers['Hash'] = crabada_checksum(data)
            final_headers['Content-Type'] = 'application/json'
            resp = requests.request(request_type, url, data=data, headers=final_headers, timeout=8).json()
        else:
            resp = requests.request(request_type, url, json=params, headers=final_headers, timeout=8).json()
        error = resp['error_code']
        if resp['error_code']:
            raise Exception('API Request failed:', error, '->', resp['message'])
        return resp['result']


def convert_list(convert_fn, res) -> list:
    res = res or []
    return list(map(convert_fn, res))
