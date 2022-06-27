#!/usr/bin/python
#
# Automatically runs battle game mining for the given account.
# The password and other options should be set in .env.

import asyncio

from bots.battle import BattleManager
from common.session_shim import shim_session_send


def main():
    print('Loading')

    bot = BattleManager()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                bot.mine_loop(),
                # bot.config.refresh_loop(),
            ))
    finally:
        loop.close()


if __name__ == '__main__':
    shim_session_send()
    main()
