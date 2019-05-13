from scrapy import Request
from scrapy.spiders import CrawlSpider
import re
import random
import base64
import os

from facebook_scraper.items import FacebookEvent, FacebookEventLoader
from facebook_scraper.lib.auth import login, login_using_response, get_credentials
from facebook_scraper.lib.ng_api import NgAPI
from facebook_scraper.lib.util import deep_merge

EVENTS_URL = 'https://mobile.facebook.com/{venue}/events'
COOKIEJAR_PREFIX = 'fb_auth_'
PROXY_POOL = os.environ.get('PROXY_POOL')


class EventsSpider(CrawlSpider):
    name = 'events'
    venues = []
    proxy_pool = []
    cookiejars = []
    ng_api = None
    city_config = {}

    def init(self, callback):
        if not hasattr(self, 'city') or not hasattr(self, 'country'):
            raise Exception('city and country are required spider arguments')

        self.ng_api = NgAPI()

        self.create_proxy_pool()
        self.get_venues()
        self.city_config = self.ng_api.get_city_config()
        return self.create_auth_sessions(callback)

    def start_requests(self):
        def init_cb():
            for venue in self.venues:
                url = EVENTS_URL.format(venue=venue['facebook']['id'])
                kwargs = self.get_request_conf()
                kwargs['meta']['venue'] = venue
                kwargs['meta']['req_conf'] = kwargs
                yield Request(url=url, callback=self.parse, **kwargs)

        return [self.init(init_cb)]

    def parse(self, response):
        event_list = response.xpath("//a[contains(@href,'/events/')]")
        next_page_url = response.css('#m_more_friends_who_like_this a::attr(href)').get()

        if response.xpath("//form[contains(@action,'login')]"):
            self.logger.debug('Login form found; logging in')
            return login_using_response(
                response,
                cookiejar=response.meta['cookiejar'],
                callback=self.parse
            )

        conf = response.meta['req_conf'].copy()
        conf['meta']['venue'] = response.meta['venue']

        # Fetch events
        for event in event_list:
            details_url = response.urljoin(event.attrib['href'])
            yield Request(url=details_url, callback=self.parse_event, **conf)

        # Fetch next page
        if next_page_url:
            url = response.urljoin(next_page_url)
            yield Request(url=url, callback=self.parse, **conf)

    def parse_event(self, response):
        loader = FacebookEventLoader(item=FacebookEvent(), response=response)

        country = response.meta['venue']['location']['country']
        city = response.meta['venue']['location']['city']
        loader.context['timezone'] = self.city_config[country][city]['timezone']

        if not re.search(r"events/(\d+)\?", response.url):
            self.logger.warn('URL not matching event url; skipping')
            return

        event_id = re.compile(r"events/(\d+)\?").search(response.url).groups()

        loader.add_value('id', event_id)
        loader.add_value('venue_id', response.meta['venue']['id'])

        loader.add_xpath("organiser_name", "//div[contains(text(),'More events at')]/text()")
        loader.add_xpath('description', "//div[@id='unit_id_886302548152152']/div[2]/text()")
        loader.add_xpath('title', "//div[@id='cta_button_bar_wrapper']/preceding-sibling::div//h3/text()")
        loader.add_xpath('location_name', "(//div[@id='event_summary']//table)[2]//td[2]/*[1]/div/text()")
        loader.add_xpath('going_count', "//div[@id='unit_id_703958566405594']/div[1]/div[1]/div[2]/a/text()")
        loader.add_xpath('interested_count', "//div[@id='unit_id_703958566405594']/div[1]/div[2]/div[2]/a/text()")
        loader.add_css('image', "#event_header img::attr(src)")

        loader.add_xpath('dates', "(//div[@id='event_summary']//table)[1]//td[2]/dd/*/*/*")
        loader.add_xpath('dates', "(//div[@id='event_summary']//table)[1]//td[2]/*[1]/div/text()")

        return loader.load_item()

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
            cookiejar='auth'
            self.cookiejars.append(cookiejar)
            return login(callback=callback, cookiejar=cookiejar)

    def create_proxy_auth_sessions(self, callback, proxy_index=0):
        if len(self.proxy_pool) > proxy_index:
            cookiejar = COOKIEJAR_PREFIX + str(proxy_index)
            self.cookiejars.append(cookiejar)
            return login(credentials=get_credentials(proxy_index),
                         callback=lambda: self.create_proxy_auth_sessions(callback, proxy_index + 1),
                         cookiejar=cookiejar)
        else:
            return callback()

    def get_venues(self):
        args = {
            'fields': 'facebook.id,location.city,location.country',
            'filters': {
                'hasFb': '1',
                'city': self.city,
                'country': self.country,
            }
        }
        self.venues = self.ng_api.get_venues(**args)
        self.logger.debug('Fetched {} venues'.format(str(len(self.venues))))
