# -*- coding: utf-8 -*-
"""
Display time and date information.

This module allows one or more datetimes to be displayed.
All datetimes share the same format_time but can set their own timezones.
Timezones are defined in the `format` using the TZ name in squiggly brackets eg
`{GMT}`, `{Portugal}`, `{Europe/Paris}`, `{America/Argentina/Buenos_Aires}`.

ISO-3166 two letter country codes eg `{de}` can also be used but if more than
one timezone exists for the country eg `{us}` the first one will be selected.

`{Local}` can be used for the local settings of your computer.

A full list of timezones can be found at
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

Configuration parameters:
    blocks: a string, where each character represents time period
        from the start of a time period.
    block_hours: length of time period for all blocks in hours (default 12)
    button_reset: button that switches display to the first timezone. setting
        to 0 disables button press (default 1)
    cycle: If more than one display then how many seconds between changing the
        display (default 10)
    format: defines the timezones displayed these can be separated by `;` for
        multiple displays that are switched between (default '{local}')
    format_time: format to use for the time, strftime directives such as `%H`
        can be used (default '{name} {icon} %c')

Format of status string placeholders:
    {icon} a character representing the time from `blocks`
    {name} friendly timezone name eg `Buenos Aires`
    {timezone} full timezone name eg America/Argentina/Buenos_Aires

Requires:
    pytz: python library
    tzlocal: python library

i3status.conf example:

```
# cycling through London, Warsaw, Tokyo
clock {
    format = "{Europe/London};{Europe/Warsaw};{Asia/Tokyo}"
    format_time = "{name} %H:%M"
}


# Show the time and date in New York
clock {
   format = "Big Apple {America/New_York}"
   format_time = "%Y-%m-%d %H:%M:%S"
}


# wall clocks
clock {
    format = "{Asia/Calcutta} {Africa/Nairobi} {Asia/Bangkok}"
    format_time = "{name} {icon}"
}
```

@author tobes
@license BSD

"""

import re
import math
from datetime import datetime
from time import time

import pytz

CLOCK_BLOCKS = '🕛🕧🕐🕜🕑🕝🕒🕞🕓🕟🕔🕠🕕🕡🕖🕢🕗🕣🕘🕤🕙🕥🕚🕦'


class Py3status:
    """
    """
    # available configuration parameters
    blocks = CLOCK_BLOCKS
    block_hours = 12
    button_reset = 1
    cycle = 10
    format = "{Local}"
    format_time = '{name} %c'

    def __init__(self):
        self._initialized = False

    def _init(self):
        # Multiple clocks are possible that can be cycled through
        if self.format:
            self.format = self.format.split(';')
        # if only one item we don't need to cycle
        if len(self.format) == 1:
            self.cycle = 0
        # find any declared timezones eg {Europe/London}
        self._items = {}
        matches = re.findall('\{([^}]*)\}', ''.join(self.format))
        for match in matches:
            self._items[match] = self._get_timezone(match)

        # workout how often in seconds we will need to do an update to keep the
        # display fresh
        format_time = re.sub('\{([^}]*)\}', '', self.format_time)
        format_time = format_time.replace('%%', '')
        if '%f' in format_time:
            # microseconds
            self.time_delta = 0
        elif '%S' in format_time:
            # seconds
            self.time_delta = 1
        elif '%c' in format_time:
            # Locale’s appropriate date and time representation
            self.time_delta = 1
        elif '%X' in format_time:
            # Locale’s appropriate time representation
            self.time_delta = 1
        else:
            self.time_delta = 60
        self._cycle_time = time() + self.cycle
        self.active = 0
        # fix for unicode issues
        self.blocks = self.blocks.decode('utf8')
        self._initialized = True

    def _get_timezone(self, tz):
        '''
        Find and return the time zone if possible
        '''
        # special Local timezone
        if tz == 'Local':
            try:
                import tzlocal
                return tzlocal.get_localzone()
            except (ImportError, pytz.UnknownTimeZoneError):
                return '?'

        # we can use a country code to get tz
        # FIXME this is broken for multi-timezone countries eg US
        # for now we just grab the first one
        if len(tz) == 2:
            try:
                zones = pytz.country_timezones(tz)
            except KeyError:
                return '?'
            tz = zones[0]

        # get the timezone
        try:
            zone = pytz.timezone(tz)
        except pytz.UnknownTimeZoneError:
            return '?'
        return zone

    def _change_active(self, diff):
        self.active = (self.active + diff) % len(self.format)

    def on_click(self, i3s_output_list, i3s_config, event):
        """
        Switch the displayed module or pass the event on to the active module
        """
        # reset cycle time
        if self.button_reset and event['button'] == self.button_reset:
            self.active = 0
            # reset the cycle time
            self._cycle_time = time() + self.cycle

    def clock(self, i3s_output_list, i3s_config):
        if not self._initialized:
            self._init()

        # cycling
        if self.cycle and time() >= self._cycle_time:
            self._change_active(1)
            self._cycle_time = time() + self.cycle

        # update our times
        times = {}
        for name, zone in self._items.items():
            if zone == '?':
                times[name] = '?'
            else:
                t = datetime.now(zone)
                format_time = self.format_time
                icon = None
                if '{icon}' in format_time:
                    # calculate the decimal hour
                    h = t.hour + t.minute / 60.
                    # make 12 hourly etc
                    h = h % self.block_hours
                    idx = int(math.floor(h / self.block_hours * (len(
                        self.blocks))))
                    icon = self.blocks[idx].encode('utf8')
                timezone = zone.zone
                tzname = timezone.split('/')[-1].replace('_', ' ')
                format_time = format_time.format(icon=icon,
                                                 name=tzname,
                                                 timezone=timezone)
                format_time = t.strftime(format_time)
                times[name] = format_time

        # work out when we need to update
        now = time()
        if self.time_delta:
            timeout = now + self.time_delta - now % self.time_delta
        else:
            timeout = 0

        # if cycling we need to make sure we update when they are needed
        if self.cycle:
            cycle_timeout = self._cycle_time
            timeout = min(timeout, cycle_timeout)

        return {
            'full_text': self.format[self.active].format(**times),
            'cached_until': timeout
        }


if __name__ == "__main__":
    """
    Test this module by calling it directly.
    """
    from time import sleep
    x = Py3status()
    config = {'color_bad': '#FF0000', 'color_good': '#00FF00', }

    while True:
        print(x.clock([], config))
        sleep(1)
