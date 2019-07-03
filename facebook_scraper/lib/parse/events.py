import re

from scrapy import Request
from scrapy.loader.processors import MapCompose

from facebook_scraper.items import FacebookEvent, FacebookEventLoader
from facebook_scraper.lib.parse.dates import is_non_date

EVENT_DATES_URL = 'https://mobile.facebook.com/event/dates/{event}'


class EventParser():
    def __init__(self, spider):
        self.spider = spider

    def parse(self, response):
        loader = FacebookEventLoader(item=FacebookEvent(), response=response)

        loader.context['timezone'] = self.spider.city_config[self.spider.page_slug]['timezone']

        event_id = re.search(r"events/(\d+)\?", response.url)
        if not event_id:
            self.logger.warning('Unexpected URL during event parsing')
            return
        else:
            event_id = event_id.groups()[0]

        loader.add_value('id', event_id)
        loader.add_value('venue_id', response.meta['venue']['id'])

        loader.add_value("organiser_name", response.meta['organiser_name'])
        loader.add_xpath("organiser_name",  # Venue name in "About the Venue block"
                         "//div[@id='unit_id_540610469432174']//a[contains(@href, 'map')]/preceding-sibling::*[2]/text()")
        loader.add_xpath('description', "//div[@id='unit_id_886302548152152']/div[2]")
        loader.add_xpath('title', "//div[@id='cta_button_bar_wrapper']/preceding-sibling::div//h3/text()")
        loader.add_xpath('location_name', "(//div[@id='event_summary']//table)[2]//td[2]/*[1]/div/text()")
        loader.add_css('image', "#event_header img::attr(src)")

        main_date_field_xpath = "(//div[@id='event_summary']//table)[1]//td[2]/*[1]/div/text()"
        # Few dates (visible on same page)
        if not is_non_date(response.xpath(main_date_field_xpath).get()):
            loader.add_xpath('dates', main_date_field_xpath)
            loader.add_xpath('interested_counts', "//div[@id='unit_id_703958566405594']/div[1]/div[2]/div[2]/a/text()")
            yield loader.load_item()
        # Multiple dates (scrape from dates page)
        else:
            req_kwargs = response.meta['req_conf'].copy()
            yield Request(url=EVENT_DATES_URL.format(event=event_id),
                          callback=lambda res: self.parse_date_page(res, loader),
                          **req_kwargs)

    def parse_date_page(self, response, loader):
        date_containers = response.xpath("//a[contains(@href, 'event_time_id')]/parent::*/parent::*")

        # Inserts whitespace between <div> and <a> element to separate date and time for the date parser
        def insert_whitespace(html):
            return re.sub(r'(.*</div>)(<a.*)', r'\1 \2', html)

        loader.add_value('dates', date_containers.select('div[1]').getall(),
                         MapCompose(insert_whitespace))

        def extract_interested_count(html):
            match = re.search(r'(\d+K?) person', html)
            if match:
                return match.groups()[0]
            else:
                # Return zero to preserve relation to date
                return '0'

        loader.add_value('interested_counts',
                         date_containers.getall(),
                         MapCompose(extract_interested_count))

        return loader.load_item()
