# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile
import jsonlines
import requests
from scrapy.exceptions import DropItem


class FacebookEventsPipeline(object):
    venue_files = {}

    def close_spider(self, spider):
        event_count = 0
        spider.logger.debug('Scraped events for {} venues'.format(len(self.venue_files.keys())))
        for venue_id in self.venue_files:
            data, images = self.handle_finished(venue_id, spider.ng_api, spider)
            event_count += len(data)
        spider.logger.debug('Processed {} events through pipeline'.format(event_count))

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
            raise DropItem

        if item.get('organiser_name') != item.get('location_name'):
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
                'dates': event['dates'],
                'facebook': {
                    'id': event['id'],
                    'description': event['description'].replace('\n', '\\n'),
                    'title': event['title'],
                }
            }
            if 'interested_count' in event:
                item['facebook']['interestedCount'] = event['interested_count']
            if 'going_count' in event:
                item['facebook']['goingCount'] = event['going_count']
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
                    spider.logger.exception('API error during pipeline closing')
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
            spider.logger.exception('API error during pipeline closing')

        return data, images

