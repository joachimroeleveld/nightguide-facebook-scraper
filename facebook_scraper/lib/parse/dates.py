import re
import datetime
import dateutil.parser as date_parser
from dateutil import tz
import logging

SINGLE_DAY_PATTERN = r"^(\w+, \d+ \w+(?: \d{4})?|\w+|\d+ \w+(?: \d{4})?) (?:from |at )?(?:(\d+:\d{2})[^\d]*(\d+:\d{2})?)"
DAY_RANGE_PATTERN = r"^(\w+, \w+ \w+(?:,? \d{4})?|\w+|\w+ \w+(?:,? \d{4})?) (?:from |at )?(?:(\d+:\d{2}(?: (?:AM|PM)))[^\d]*(\d+:\d{2}(?: (?:AM|PM)))?)"


def parse_date(date_string, timezone):
    match_single = re.match(SINGLE_DAY_PATTERN, date_string)
    tzinfo = tz.gettz(timezone)
    if match_single:
        groups = match_single.groups()
        return parse_date_string_parts(tzinfo, groups[0], groups[1], groups[2])
    match_range = re.match(DAY_RANGE_PATTERN, date_string)
    if match_range:
        day_from, time_from, day_to, time_to = match_range.groups()
        return parse_date_string_parts(tzinfo, day_from, time_from, time_to, day_to)
    logging.warning('Unmatched date string: {}'.format(date_string))


def parse_date_string_parts(tzinfo, day_from, time_from, time_to=None, day_to=None):
    same_day = not day_to
    if same_day:
        day_to = day_from
    date_from = date_parser.parse(str.join(' ', [day_from, time_from]), fuzzy=True).replace(tzinfo=tzinfo)
    # With ending time
    if time_to:
        date_to = date_parser.parse(str.join(' ', [day_to, time_to]), fuzzy=True).replace(tzinfo=tzinfo)
        # If on the same day after midnight
        if same_day and time_to < time_from:
            date_to = date_to + datetime.timedelta(days=1)
        return date_from, date_to
    # No ending time
    else:
        return date_from,


def is_non_date(item):
    lower = item.lower()
    words = [
        # Every Thursday, until 28 Jun
        'every',
        # 3 more dates
        'dates',
        # +7 more times
        'times',
        # Until 23 Sep
        'until'
    ]
    return len([word for word in words if word in lower]) > 0
