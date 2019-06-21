import requests
from urllib.parse import urlencode
import os

PAGE_SIZE = 50
BASE_URL = os.environ.get('NG_API_HOST')
TOKEN = os.environ.get('NG_API_TOKEN')

class NgAPI:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = TOKEN

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
        if not res.status_code == requests.codes.ok:
            res.raise_for_status()
        return res
