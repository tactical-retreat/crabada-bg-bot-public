import os
import sys

DEV_MODE = False


class Config(object):
    def __init__(self):
        self.process = os.path.basename(sys.argv[0])

    @property
    def address(self) -> str:
        """Address associated with the loaded keyfile."""
        return 'fake_address'

    @property
    def discord_webhook(self) -> str:
        """Discord webhook URL for posting status."""
        return ''

    @property
    def webhook_critical_ping_user(self) -> int:
        """Discord user ID to ping for critical updates."""
        return 0

    # @property
    # def webhook_loot_ping_role(self) -> int:
    #     """Discord role ID to ping for loot ready announcements."""
    #     return 0

    @property
    def battle_poll_interval(self) -> int:
        return 30

    @property
    def battle_minimum_looter_level(self) -> int:
        return 3

    @property
    def battle_minimum_advantage(self) -> int:
        return 6

    @property
    def battle_self_badcomp_penalty(self) -> int:
        return 8

    @property
    def battle_enemy_badcomp_penalty(self) -> int:
        return 4

    @property
    def battle_auto_level(self) -> bool:
        return False

    @property
    def battle_auto_withdraw(self) -> bool:
        return False

    @property
    def battle_auto_send_address(self) -> str:
        return ''

    @property
    def battle_auto_bridge(self) -> bool:
        return False

    @property
    def battle_tip(self) -> int:
        return 0

    @property
    def battle_auto_swap(self) -> bool:
        return False


DEFAULT_CONFIG: Config = Config()
