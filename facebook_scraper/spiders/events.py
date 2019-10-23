from scrapy import Request
from scrapy.spiders import CrawlSpider
import random
import base64
import os

from facebook_scraper.lib.auth import login
from facebook_scraper.lib.ng_api import NgAPI
from facebook_scraper.lib.util import deep_merge
from facebook_scraper.lib.parse.events import EventParser
from facebook_scraper.lib.sheets import get_additional_event_ids

EVENTS_URL = 'https://mobile.facebook.com/{venue}/events'
EVENT_URL = 'https://mobile.facebook.com/events/{event}'
COOKIEJAR_PREFIX = 'fb_auth_'
PROXY_POOL = os.environ.get('PROXY_POOL')


class EventsSpider(CrawlSpider):
    name = 'events'
    venues = []
    proxy_pool = []
    cookiejars = []
    ng_api = None
    city_config = {}
    event_parser = None
    additional_events = ()

    def init(self, callback):
        if not hasattr(self, 'page_slug'):
            raise Exception('page_slug is a required spider argument')
        if hasattr(self, 'event_ids') and not hasattr(self, 'venue_id'):
            raise Exception('venue_id is required if event_ids is set')

        self.ng_api = NgAPI(logger=self.logger, stats=self.crawler.stats)
        self.create_proxy_pool()

        self.event_parser = EventParser(self)

        self.event_ids = self.event_ids.split(',') if hasattr(self, 'event_ids') else None

        venue_ids = None
        if hasattr(self, 'venue_ids'):
            venue_ids = self.venue_ids.split(',')
        if hasattr(self, 'venue_id'):
            venue_ids = [self.venue_id]
        self.fetch_venues(ids=venue_ids)

        self.city_config = self.ng_api.get_city_config()

        if not self.event_ids:
            try:
                self.additional_events = get_additional_event_ids(self.page_slug)
            except Exception:
                self.logger.error('Could not fetch additional event ids')

        return self.create_auth_sessions(callback)

    def start_requests(self):
        def init_cb():
            for venue in self.venues:
                req_kwargs = self.get_request_conf()
                req_kwargs['meta']['req_conf'] = req_kwargs.copy()
                req_kwargs['meta']['venue'] = venue

                additional_events = self.additional_events[venue['id']] if venue['id'] in self.additional_events else None
                if additional_events:
                    self.logger.debug(
                        'Found {} additional events for venue {}'.format(str(len(additional_events)),
                                                                         venue['id']))
                    req_kwargs['meta']['additional_events'] = additional_events

                url = EVENTS_URL.format(venue=venue['facebook']['id'])
                yield Request(url=url, callback=self.parse_events_page, **req_kwargs)

        return [self.init(init_cb)]

    def parse_events_page(self, response):
        event_urls = []
        known_event_ids = self.event_ids if self.event_ids else []

        if not self.event_ids and 'additional_events' in response.meta:
            known_event_ids += response.meta['additional_events']

        if known_event_ids:
            event_urls += list(map(lambda event_id: EVENT_URL.format(event=event_id), known_event_ids))

        # Get URLs from event page
        if not self.event_ids:
            event_elems = response.xpath("//div/a[contains(@href,'/events/')][1]")
            event_urls += list(map(lambda elem: response.urljoin(elem.attrib['href']), event_elems))

        # Prepare request args
        req_kwargs = response.meta['req_conf'].copy()
        req_kwargs['meta']['req_conf'] = req_kwargs
        req_kwargs['meta']['venue'] = response.meta['venue']

        is_first_page = 'serialized_cursor' not in response.url

        # Get organiser name
        if is_first_page:
            req_kwargs['meta']['organiser_name'] = response.xpath(
                "//div[@id='msite-pages-header-contents']//h1//span[1]/text()").get()

        # Set stats
        if is_first_page and not self.event_ids:
            if len(event_urls):
                self.crawler.stats.inc_value('events_spider/venues_with_events')
            else:
                self.crawler.stats.inc_value('events_spider/venues_without_events')

        # Fetch events
        for event_url in event_urls:
            yield Request(url=event_url, callback=self.event_parser.parse, **req_kwargs)

        # Fetch next pages
        if not self.event_ids:
            if hasattr(self, 'event_page_depth'):
                if 'page_depth' in req_kwargs['meta']:
                    req_kwargs['meta']['event_page_depth'] += 1
                else:
                    req_kwargs['meta']['event_page_depth'] = 1

                if req_kwargs['meta']['event_page_depth'] == int(self.event_page_depth):
                    return

            next_page_url = response.css('#m_more_friends_who_like_this a::attr(href)').get()
            if next_page_url:
                url = response.urljoin(next_page_url)
                yield Request(url=url, callback=self.parse_events_page, **req_kwargs)

    def get_request_conf(self):
        conf = {'meta': {}}
        if self.proxy_pool:
            proxy_index = random.randint(0, len(self.proxy_pool) - 1)
            deep_merge(self.get_request_auth_conf(proxy_index), conf)
            deep_merge(self.get_request_proxy_conf(proxy_index), conf)
        else:
            deep_merge(self.get_request_auth_conf(), conf)
        return conf

    def get_request_proxy_conf(self, proxy_index):
        proxy = self.proxy_pool[proxy_index]
        conf = {'meta': {}, 'headers': {}}
        address, un, password = proxy
        conf['meta']['proxy'] = address
        if un:
            auth_string = base64.b64encode(bytes('{}:{}'.format(un, password), 'utf8')).decode('utf8')
            conf['headers']['Proxy-Authorization'] = 'Basic {}'.format(auth_string)
        return conf

    def get_request_auth_conf(self, proxy_index=0):
        conf = {'meta': {}}
        conf['meta']['cookiejar'] = self.cookiejars[proxy_index]
        return conf

    def create_proxy_pool(self):
        if PROXY_POOL:
            proxy_pool = PROXY_POOL.split(',')
            for proxy in proxy_pool:
                ip, port, un, password = proxy.split(':')
                address = 'http://{}:{}'.format(ip, port)
                self.proxy_pool.append((address, un, password))

    def create_auth_sessions(self, callback):
        if self.proxy_pool:
            return self.create_proxy_auth_sessions(callback)
        else:
            cookiejar = 'auth'
            self.cookiejars.append(cookiejar)
            return login(callback=callback, **self.get_request_auth_conf())

    def create_proxy_auth_sessions(self, callback, proxy_index=0):
        if len(self.proxy_pool) > proxy_index:
            cookiejar = COOKIEJAR_PREFIX + str(proxy_index)
            self.cookiejars.append(cookiejar)

            kwargs = self.get_request_auth_conf(proxy_index)
            deep_merge(self.get_request_proxy_conf(proxy_index), kwargs)
            return login(callback=lambda: self.create_proxy_auth_sessions(callback, proxy_index + 1), **kwargs)
        else:
            return callback()

    def fetch_venues(self, ids):
        args = {
            'fields': 'facebook.id,pageSlug',
            'filters': {
                'hasFb': '1',
                'pageSlug': self.page_slug
            }
        }
        if ids:
            args['filters']['ids'] = str.join(',', ids)

        self.venues = self.ng_api.get_venues(**args)

        self.crawler.stats.set_value('events_spider/venue_count', len(self.venues))
        self.logger.debug('Fetched {} venues'.format(str(len(self.venues))))
