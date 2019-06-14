# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import re
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Join
from facebook_scraper.lib.parse_dates import parse_date
from scrapy.utils.markup import remove_tags
import lxml.html.clean as clean


class FacebookEvent(scrapy.Item):
    venue_id = scrapy.Field()
    id = scrapy.Field()
    title = scrapy.Field()
    dates = scrapy.Field()
    description = scrapy.Field()
    organiser_name = scrapy.Field()
    location_name = scrapy.Field()
    image = scrapy.Field()
    interested_count = scrapy.Field()
    going_count = scrapy.Field()
    pass


def format_dates(self, dates):
    def formatter(d):
        return d.isoformat()

    def iterator(date):
        val = {'from': formatter(date[0])}
        if len(date) == 2:
            val['to'] = formatter(date[1])
        return val

    return list(map(iterator, [x for x in dates if x is not None]))


def dates_in(self, dates, loader_context):
    def filter_non_dates(item):
        lower = item.lower()
        # Every Thursday, until 28 Jun
        if "every" in lower:
            return False
        # 3 more dates
        if "dates" in lower:
            return False
        # +7 more times
        if "times" in lower:
            return False
        return True

    timezone = loader_context.get('timezone')
    sanitized = map(remove_tags, dates)
    filtered = filter(filter_non_dates, sanitized)
    parsed = map(lambda item: parse_date(item, timezone), filtered)
    return list(parsed)


def count_in(self, value):
    if value:
        count = value[0]
        multiplier = 1
        if 'K' in count:
            count = count.replace('K', '')
            multiplier = 1000
        return int(float(count) * multiplier)
    else:
        return None


def description_out(self, value):
    if value:
        safe_attrs = {'src', 'alt', 'href', 'title', 'width', 'height'}
        kill_tags = ['object', 'iframe', 'div', 'span']
        cleaner = clean.Cleaner(safe_attrs_only=True, safe_attrs=safe_attrs, kill_tags=kill_tags)
        return cleaner.clean_html(value[0])
    else:
        return None


def organiser_name_in(self, name):
    if name:
        return re.search(r"events at (.*)", name[0]).groups()
    return None


class FacebookEventLoader(ItemLoader):
    default_output_processor = TakeFirst()

    organiser_name_in = organiser_name_in

    description_out = description_out

    dates_in = dates_in
    dates_out = format_dates

    interested_count_in = count_in
    going_count_in = count_in
