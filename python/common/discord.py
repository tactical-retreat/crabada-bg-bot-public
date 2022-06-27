import os
import sys
import time
from typing import Optional

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
from web3 import Web3
from web3.types import TxReceipt

from common.config_local import DEFAULT_CONFIG
from common.git import fetch_version

LOOT_WEBHOOK = 'not for yu'


def post_webhook(webhook_url: str, msg: str):
    """Posts a very simple webhook message to the provided url."""
    print(f'Posting webhook: {msg}')
    result = requests.post(webhook_url, json={"content": msg})
    result.raise_for_status()


def safe_post_webhook(webhook_url: str, msg: str):
    """Posts a very simple webhook message to the provided URL, swallowing errors."""
    try:
        post_webhook(webhook_url, msg)
        time.sleep(.5)  # Prevent rate limiting
    except Exception as err:
        print(f'Webhook failed: {err}')


class AlertManager(object):
    """Utility for tracking what we're doing, what happened, and alerting on it."""

    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.total_gas_used_wei = 0
        self.tus_remaining = 0

        self.action = ''
        self.team_id = 0
        self.game_id = 0

        self.tx_hash = ''
        self.gas_used_wei = 0

        self.warn_error_escalation_text = ''

    def start_action(self, action: str, team_id: int, game_id: Optional[int] = None):
        self.reset()
        self.action = action
        self.team_id = team_id
        self.game_id = game_id

    def tx_done(self, receipt: TxReceipt, extra_info: str = None,
                gas_override: int = None, icon: str = None):
        self.tx_hash = receipt.transactionHash.hex()
        self.gas_used_wei = gas_override or (receipt.gasUsed * receipt.effectiveGasPrice)
        self.total_gas_used_wei += self.gas_used_wei
        explorer_link = f'https://subnets.avax.network/swimmer/mainnet/explorer/tx/{self.tx_hash}'

        if not receipt.status:
            content = f'[TX]({explorer_link}) unexpectedly failed. Check logs for more information.'
            print(f'TX Error: {receipt}')
            self.error(content, icon=icon)
        else:
            content = (extra_info or 'Succeeded') + f' - [TX]({explorer_link})'
            self.ok(content, icon=icon)

    def ok(self, content: str, icon: str = None):
        self.post_webhook(self.action, content, '00A427', icon=icon)

    def warn(self, content: str, icon: str = None):
        if self.warn_error_escalation_text:
            content += f' - Critical because: {self.warn_error_escalation_text}'
            self.critical(content, icon=icon)
            return
        self.post_webhook(self.action, content, 'FFA500', icon=icon, unexpected_status='Transient Error')

    def error(self, content: str, icon: str = None):
        if self.warn_error_escalation_text:
            content += f' - Critical because: {self.warn_error_escalation_text}'
            self.critical(content, icon=icon)
            return
        self.post_webhook(self.action, content, 'CC0000', icon=icon, unexpected_status='Error')

    def priority(self, content: str, icon: str = None):
        if not self.config.webhook_critical_ping_user:
            content += ' - configure a DISCORD_PING_USER'
        self.post_webhook(self.action, content, 'FFA500', icon=icon,
                          mention=self.config.webhook_critical_ping_user,
                          unexpected_status='Priority Event')

    def loot_available(self, content: str, icon: str = None):
        # if not self.config.webhook_critical_ping_user and not self.config.webhook_loot_ping_role:
        #     content += ' - configure a DISCORD_PING_USER or DISCORD_LOOT_PING_ROLE'
        self.post_webhook(self.action, content, 'FFA500', icon=icon,
                          mention=self.config.webhook_critical_ping_user,
                          # mention_role=self.config.webhook_loot_ping_role,
                          unexpected_status='Priority Event')

    def critical(self, content: str, icon: str = None):
        if not self.config.webhook_critical_ping_user:
            content += ' - please configure a DISCORD_PING_USER'
        self.post_webhook(self.action, content, 'CC0000', icon=icon,
                          mention=self.config.webhook_critical_ping_user,
                          unexpected_status='Critical Error')

    def webhook_context(self) -> str:
        if not self.team_id:
            return 'Unexpected internal failure in ' + os.path.basename(sys.argv[0])
        v = f'Team {self.team_id}'
        if self.game_id:
            v += f' in Game {self.game_id}'
        return v

    def footer(self) -> str:
        parts = []
        if self.gas_used_wei:
            parts.append(f'Gas {fmt_gas(self.gas_used_wei)} / Total {fmt_gas(self.total_gas_used_wei)}')
        if self.tus_remaining:
            parts.append(f'TUS: {round(self.tus_remaining, 0)}')
        parts.append(f'v{fetch_version()}')
        return ' | '.join(parts)

    def post_webhook(self, action: str, content: str, color: str, icon: str = None,
                     mention: int = None, mention_role: int = 0, unexpected_status: str = ''):
        print(self.webhook_context(), '-', action, '-', content)
        if self.tx_hash:
            print(f'TX: {self.tx_hash}')
        if not self.config.discord_webhook:
            return

        try:
            url = [self.config.discord_webhook]
            if 'Miner stats' in content or 'Looting mine' in content:
                # This is so fucking awful
                url.append(LOOT_WEBHOOK)

            webhook = DiscordWebhook(url=url)
            if mention:
                webhook.set_content(f'<@{mention}>')
            if mention_role:
                if webhook.content:
                    webhook.content += ' - '
                else:
                    webhook.content = ''
                webhook.content += f'<@&{mention_role}>'

            title = self.webhook_context() + ' - ' + action
            title_url = f'https://crabadatracker.app/profile/{self.config.address}'

            embed = DiscordEmbed(
                title=title,
                url=title_url,
                description=content,
                color=color,
                rate_limit_retry=True)
            embed.set_footer(text=self.footer())
            if unexpected_status:
                embed.set_author(name=unexpected_status)
            embed.set_timestamp()
            if icon:
                embed.set_thumbnail(url=icon)
            webhook.add_embed(embed)
            webhook.execute()
        except Exception as ex:
            print(f'Failed to send webhook! {ex}')
            print(action, content, self.webhook_context(), self.footer())
        finally:
            self.reset()

    def reset(self):
        self.action = ''
        self.team_id = 0
        self.game_id = 0
        self.tx_hash = ''
        self.gas_used_wei = 0.0
        self.warn_error_escalation_text = ''

    def simple_embed(self, action: str, content: str, mention: int = None):
        print('-', action, '-', content, '-', mention)
        if not self.config.discord_webhook:
            return

        try:
            url = [self.config.discord_webhook]
            webhook = DiscordWebhook(url=url)
            if mention:
                webhook.set_content(f'<@{mention}>')
            title = action
            title_url = f'https://crabadatracker.app/profile/{self.config.address}'

            embed = DiscordEmbed(
                title=title,
                url=title_url,
                description=content,
                rate_limit_retry=True)
            embed.set_timestamp()
            embed.set_footer(text=self.footer())
            webhook.add_embed(embed)
            webhook.execute()
        except Exception as ex:
            print(f'Failed to send webhook! {ex}')
            print(action, content)


def fmt_gas(gas_in_wei: int) -> str:
    return str(round(Web3.fromWei(gas_in_wei, 'ether'), 1))
