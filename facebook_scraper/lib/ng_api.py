import requests
from urllib.parse import urlencode
import os

PAGE_SIZE = 50
BASE_URL = os.environ.get('NG_API_HOST')
TOKEN = os.environ.get('NG_API_TOKEN')


class NgAPI:
    def __init__(self, logger, stats):
        self.base_url = BASE_URL
        self.token = TOKEN
        self.logger = logger
        self.stats = stats

    def get_city_config(self):
        return self._request('/misc/city-config').json()

    def update_venue_facebook_events(self, venue_id, events):
        uri = '/venues/{}/facebook-events'.format(venue_id)
        self._request(uri=uri, method='PUT', json=events)

    def update_facebook_event_image(self, fb_event_id, image_url):
        uri = '/events/facebook-events/{}/image'.format(fb_event_id)
        json = {'image': {'url': image_url}}
        self._request(uri, method='PUT', json=json)

    def get_venues(self, filters={}, venues=[], **kwargs):
        query = {
            'limit': PAGE_SIZE,
            'offset': str(len(venues)),
        }
        query.update(kwargs)
        query.update(filters)

        uri = '/venues?' + urlencode(query)
        body = self._request(uri).json()

        venues.extend(body['results'])
        if body['totalCount'] == len(venues):
            return venues

        return self.get_venues(filters, venues, **kwargs)

    def _request(self, uri, method='GET', **kwargs):
        url = self.base_url + uri
        headers = {'Authorization': 'Bearer ' + self.token}
        res = requests.request(method=method, url=url, headers=headers, **kwargs)

        self.stats.inc_value('ng_api/request_count')
        if not res.status_code == requests.codes.ok:
            body = None
            try:
                body = res.json()
            except ValueError:
                pass
            extra = {'code': res.status_code, 'response': body}
            self.logger.error('An API error occurred', extra=extra)
            self.stats.inc_value('ng_api/error_count')
            self.stats.inc_value('ng_api/error_status_{}'.format(str(res.status_code)))

            res.raise_for_status()

        return res
