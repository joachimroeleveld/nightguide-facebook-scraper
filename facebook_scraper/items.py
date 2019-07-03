# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose
from facebook_scraper.lib.parse.dates import parse_date
from scrapy.utils.markup import remove_tags
from lxml import html
from lxml.html.clean import Cleaner


class FacebookEvent(scrapy.Item):
    venue_id = scrapy.Field()
    id = scrapy.Field()
    title = scrapy.Field()
    dates = scrapy.Field()
    description = scrapy.Field()
    organiser_name = scrapy.Field()
    location_name = scrapy.Field()
    image = scrapy.Field()
    interested_counts = scrapy.Field()
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
    timezone = loader_context.get('timezone')
    sanitized = map(remove_tags, dates)
    parsed = map(lambda item: parse_date(item, timezone), sanitized)
    return list(parsed)


def count_out(value):
    count = value
    multiplier = 1
    if 'K' in value:
        count = count.replace('K', '')
        multiplier = 1000
    return int(float(count) * multiplier)


def description_out(self, value):
    if value:
        safe_attrs = {'src', 'alt', 'href', 'title', 'width', 'height'}
        kill_tags = ['object', 'iframe']
        cleaner = Cleaner(safe_attrs_only=True, add_nofollow=True, safe_attrs=safe_attrs, kill_tags=kill_tags)
        cleaned = cleaner.clean_html(value[0])

        doc = html.fromstring(cleaned)
        doc.make_links_absolute('https://www.facebook.com/')

        return html.tostring(doc).decode('utf-8')
    else:
        return None


class FacebookEventLoader(ItemLoader):
    default_output_processor = TakeFirst()

    description_out = description_out

    dates_in = dates_in
    dates_out = format_dates

    interested_counts_out = MapCompose(count_out)
