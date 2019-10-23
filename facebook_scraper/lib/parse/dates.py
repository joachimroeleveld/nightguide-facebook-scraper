import re
import datetime
from datetime import timedelta
import logging
import dateparser

SUB_PATTERNS = {
    'day': r"((?:\w+,?(?: \w+)*?(?: \w+)*?)(?:,? \d{4})?)",
    'time': r"(\d{1,2}(?::\d{2})?(?: (?:AM|PM))?)",
    'time_start': r"(?:from |at )",
    'separator': r"[\s–—-]*",  # Different types of dashes
    'timezone': r"(?: UTC\+\d{2})?"
}

# ^((?:\w+,?(?: \w+)*?(?: \w+)*?)(?:,? \d{4})?) (?:from |at )?(\d{1,2}(?::\d{2})?(?: (?:AM|PM))?)(?:[\s–—-]*(\d{1,2}(?::\d{2})?(?: (?:AM|PM))?))?(?: UTC\+\d{2})?$
SINGLE_DAY_PATTERN = r"^{day} {time_start}?{time}(?:{separator}{time})?{timezone}$".format(**SUB_PATTERNS)
# ^((?:\w+,?(?: \w+)*?(?: \w+)*?)(?:,? \d{4})?) (?:from |at )?(\d{1,2}(?::\d{2})?(?: (?:AM|PM))?)[\s–—-]*((?:\w+,?(?: \w+)*?(?: \w+)*?)(?:,? \d{4})?) (?:from |at )?(\d{1,2}(?::\d{2})?(?: (?:AM|PM))?)(?: UTC\+\d{2})?$
DAY_RANGE_PATTERN = r"^{day} {time_start}?{time}{separator}{day} {time_start}?{time}{timezone}$".format(**SUB_PATTERNS)


# print('Patterns:')
# print(SINGLE_DAY_PATTERN)
# print(DAY_RANGE_PATTERN)


def parse_date(date_string, timezone, dates_are_correct):
    match_single = re.match(SINGLE_DAY_PATTERN, date_string)
    if match_single:
        groups = match_single.groups()
        return parse_date_string_parts(timezone, groups[0], groups[1], groups[2], dates_are_correct=dates_are_correct)
    match_range = re.match(DAY_RANGE_PATTERN, date_string)
    if match_range:
        day_from, time_from, day_to, time_to = match_range.groups()
        return parse_date_string_parts(timezone, day_from, time_from, time_to, day_to,
                                       dates_are_correct=dates_are_correct)
    logging.warning('Unmatched date string: {}'.format(date_string))


def parse_date_string_parts(timezone, day_from, time_from, time_to=None, day_to=None, dates_are_correct=True):
    # Account for the fact that FB displays date incorrect when the event is recurring
    date_delta = timedelta(days=0)
    if not dates_are_correct:
        date_delta = timedelta(days=-1)

    same_day = not day_to
    if same_day:
        day_to = day_from

    parse_args = {'languages': ['en'], 'settings': {'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True}}

    date_from = dateparser.parse(str.join(' ', [day_from, time_from]), **parse_args) + date_delta

    # With ending time
    if time_to:
        date_to = dateparser.parse(str.join(' ', [day_to, time_to]), **parse_args) + date_delta

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
