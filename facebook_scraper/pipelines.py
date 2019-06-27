# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile
import jsonlines
import requests
import pprint
import os
from scrapy.exceptions import DropItem
from scrapy.mail import MailSender


class FacebookEventsPipeline(object):
    venue_files = {}

    def close_spider(self, spider):
        spider.logger.debug('Scraped events for {} venues'.format(len(self.venue_files.keys())))

        event_count = 0
        for venue_id in self.venue_files:
            data, images = self.handle_finished(venue_id, spider.ng_api, spider)
            event_count += len(data)

        spider.crawler.stats.set_value('events_spider/pipeline/events_total_count', event_count)
        spider.logger.debug('Processed {} events through pipeline'.format(event_count))

        if os.getenv('ENV') == 'production':
            self.send_summary_email(spider)

    # Buffer to file
    def process_item(self, item, spider):
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
            raise DropItem

        if item.get('organiser_name') != item.get('location_name'):
            spider.crawler.stats.inc_value('events_spider/pipeline/dropped_reason_nonmatching_organiser_location')
            spider.logger.debug('Dropping item: organiser name and location name not equal')
            raise DropItem

        if venue_id not in self.venue_files:
            self.venue_files[venue_id] = NamedTemporaryFile('w+b')

        file = self.venue_files[venue_id]
        with jsonlines.open(file.name, mode='a', flush=True) as writer:
            writer.write(dict(item))

        return item

    # Send result to API
    def handle_finished(self, venue_id, ng_api, spider):
        file = self.venue_files[venue_id]
        with jsonlines.open(file.name, mode='r') as reader:
            events = []
            for event in reader:
                events.append(event)
        file.close()

        data = []
        images = []
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
                interested_count = event['interested_counts'][date_index]
                if interested_count > 0:
                    date_copy['interestedCount'] = interested_count
                item['dates'].append(date_copy)
            if 'image' in event:
                images.append((event['id'], event['image']))
            data.append(item)

        try:
            spider.logger.debug('Sending {} events to API for venue {}'.format(len(data), venue_id))
            ng_api.update_venue_facebook_events(venue_id, data)

            for fb_event_id, image_url in images:
                try:
                    ng_api.update_facebook_event_image(fb_event_id, image_url)
                except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
                    spider.logger.exception('Failed updating Facebook event image')
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
            spider.logger.exception('Failed updating Facebook events for venue')

        return data, images

    def send_summary_email(self, spider):
        spider.logger.debug('Sending summary email')

        mailer = MailSender.from_settings(spider.settings)
        intro = "Summary stats from Scrapy spider: \n\n"
        body = spider.crawler.stats.get_stats()
        body = pprint.pformat(body)
        body = intro + body
        mailer.send(to=['joachim@nightguide.app'], subject="{} FB event crawler results".format(spider.city), body=body)
