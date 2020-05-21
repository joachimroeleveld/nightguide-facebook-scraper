# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile
import jsonlines
import requests
import pprint
import os
import re
from scrapy.exceptions import DropItem
from scrapy.mail import MailSender

VENUE_LOCATION_MATCHERS = {
    # DC10 Ibiza
    '5d1afff3bd44b9001205a743': r'DC10(?: Ibiza)?',
    # Boat club
    '5d1affc9bd44b9001205a72e': r'(?:Cirque de la Nuit Ibiza|Ibiza Boat Club)',
    '5d972c5197cb4200182954f3': r'Escape (- )?Amsterdam',
    # Melkweg
    '5da46c1621b9510012acfee2': r'(?:Melkweg Amsterdam|EncoreAmsterdam)'
}


class FacebookEventsPipeline(object):
    venue_files = {}

    def close_spider(self, spider):
        spider.logger.debug('Scraped events for {} venues'.format(len(self.venue_files.keys())))

        event_count = 0
        for venue_id in self.venue_files:
            processed = self.handle_finished(venue_id, spider.ng_api, spider)
            event_count += len(processed)

        spider.crawler.stats.set_value('events_spider/pipeline/events_total_count', event_count)
        spider.logger.debug('Processed {} events through pipeline'.format(event_count))

        if os.getenv('ENV') == 'production':
            self.send_summary_email(spider)

    # Buffer to file
    def process_item(self, item, spider):
        id = item.get('id')
        venue_id = item.get('venue_id')

        required_fields = [
            'venue_id',
            'id',
            'title',
            'dates',
            'description',
            'organiser_name',
            'location_name',
        ]
        missing_fields = [field for field in required_fields if not item.get(field)]
        if missing_fields:
            spider.logger.debug('Dropping item: missing required fields: ' + str.join(', ', missing_fields))
            for field in missing_fields:
                spider.crawler.stats.inc_value('events_spider/pipeline/dropped_reason_missing_field_{}'.format(field))
                spider.logger.debug('Dropping item (id {id}): missing field {field}'.format(id=id, field=field))
            raise DropItem

        if not self.check_matching_organiser_location(item):
            spider.crawler.stats.inc_value('events_spider/pipeline/dropped_reason_nonmatching_organiser_location')
            spider.logger.debug('Dropping item (id {}): organiser name and location name not equal'.format(id))
            raise DropItem

        if venue_id not in self.venue_files:
            self.venue_files[venue_id] = NamedTemporaryFile('w+b')

        file = self.venue_files[venue_id]
        with jsonlines.open(file.name, mode='a', flush=True) as writer:
            writer.write(dict(item))

        return item

    def check_matching_organiser_location(self, item):
        if item['venue_id'] in VENUE_LOCATION_MATCHERS:
            matcher = VENUE_LOCATION_MATCHERS[item['venue_id']]
            return re.search(matcher, item['location_name']) is not None
        else:
            return item['location_name'] == item['organiser_name']

    # Send result to API
    def handle_finished(self, venue_id, ng_api, spider):
        file = self.venue_files[venue_id]
        with jsonlines.open(file.name, mode='r') as reader:
            events = []
            for event in reader:
                events.append(event)
        file.close()

        data = []
        images = {}
        for event in events:
            item = {
                'dates': [],
                'facebook': {
                    'id': event['id'],
                    'description': event['description'].replace('\n', '\\n'),
                    'title': event['title'],
                }
            }

            for date_index, date in enumerate(event['dates']):
                date_copy = date.copy()
                if 'interested_counts' in event and event['interested_counts'][date_index] > 0:
                    date_copy['interestedCount'] = event['interested_counts'][date_index]
                item['dates'].append(date_copy)

            data.append(item)

            if 'image' in event and not hasattr(spider, 'without_images'):
                images[event['id']] = event['image']

        try:
            spider.logger.debug('Sending {} events to API for venue {}'.format(len(data), venue_id))
            ng_api.update_venue_facebook_events(venue_id, data)

            # Upload images
            for event_id, image in images.items():
                try:
                    fb_event = ng_api.get_facebook_event(event_id)
                    has_fb_image = fb_event and 'images' in fb_event and [x for x in fb_event['images'] if
                                                                          'extraData' in x and 'fbUrl' in x[
                                                                              'extraData']]
                    if not has_fb_image:
                        try:
                            ng_api.update_facebook_event_image(event_id, image)
                            spider.crawler.stats.inc_value('events_spider/pipeline/uploaded_images')
                        except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
                            spider.logger.exception(
                                'Failed updating Facebook event image {} for event {}'.format(image,
                                                                                              event_id))
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        break
                    raise e
                except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
                    spider.logger.exception('Failed fetching Facebook event {}'.format(event_id))
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
            spider.logger.exception('Failed updating Facebook events for venue {}'.format(venue_id))

        return data

    def send_summary_email(self, spider):
        spider.logger.debug('Sending summary email')

        mailer = MailSender.from_settings(spider.settings)
        intro = "Summary stats from Scrapy spider: \n\n"
        body = spider.crawler.stats.get_stats()
        body = pprint.pformat(body)
        body = intro + body
        mailer.send(to=['joachim@nightguide.app'], subject="{} FB event crawler results".format(spider.page_slug),
                    body=body)
