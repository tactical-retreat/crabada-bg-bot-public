from datetime import datetime, timedelta
from typing import Dict

from dateutil.tz import gettz

from common.dates import pretty_time


class CooldownManager(object):
    """Used to prevent actions from happening too often."""

    def __init__(self, name: str, cooldown_sec: int):
        self.name = name
        self.cooldown_sec = cooldown_sec
        self.team_cooldowns: Dict[int, datetime] = {}

    def check_cooldown(self, team_id: int, do_cooldown_log: bool = True) -> bool:
        if not self.cooldown_sec:
            # This cooldown is disabled (perhaps by user config) and should be ignored.
            return True

        cur_cooldown = self.team_cooldowns.get(team_id, datetime.now())
        if datetime.now() >= cur_cooldown:
            print('Updating', self.name, 'cooldown for', team_id, 'to', cur_cooldown.strftime("%H:%M:%S"))
            self.team_cooldowns[team_id] = datetime.now() + timedelta(seconds=self.cooldown_sec)
            return True

        if do_cooldown_log:
            time_until = pretty_time((cur_cooldown - datetime.now()).seconds)
            print('Cooldown for', self.name, 'on', team_id, 'expires in', time_until)
        return False


class DateCooldown(object):
    """Track if we've passed a specific hour/minute on a date.

    This is useful to determine if we should do once a day actions.
    """

    def __init__(self, hour: int, minute: int):
        self.hour = hour
        self.minute = minute
        self.seen_date = self.get_date()

    def check_date(self) -> bool:
        """If we passed the 'seen' date since the last check, update it and return True."""
        new_date = self.get_date()
        if self.seen_date == new_date:
            return False
        print(f'Updating date from {self.seen_date} to {new_date}')
        self.seen_date = new_date
        return True

    def get_date(self):
        """Get the current date as adjusted by the specified hour/minute."""
        tz = gettz('utc')
        seen_date = datetime.now(tz=tz)
        is_after_hour = seen_date.hour > self.hour
        is_after_minute_in_hour = seen_date.hour == self.hour and seen_date.minute >= self.minute
        if is_after_hour or is_after_minute_in_hour:
            return seen_date.date()
        prev_date = seen_date - timedelta(days=1)
        return prev_date.date()
