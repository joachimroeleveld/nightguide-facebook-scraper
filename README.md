# facebook-scraper

[Scrapy](https://scrapy.org/) scraper that scrapes and normalizes data from Facebook events given a list of organisers. 

## Deployment

Build egg:
`scrapyd-deploy --build-egg output.egg`

Upload egg to Spiderkeeper

### Google auth

`facebook-scraper-sa` kubernetes secret has to contain Google application credentials.

## Configuration

### Service account

To run the spider, it's needed to add `facebook-scaper` service account key as `google-key.json` at the root of the project.

### Spider arguments

 - `page_slug` (required)
 - `without_images`
 - `event_page_depth`
 - `venue_id` or `venue_ids`
 - `event_ids` (required to also set `venue_id`)
 
E.g. `scrapy crawl events -a page_slug=nl/utrecht`
 
### Environment variables

Create `.env` under `/facebook_scraper`


## Luminati proxy

Start proxy

`docker run -p 22999:22999 -p 24000:24000 luminati/luminati-proxy luminati --www_whitelist_ips "172.17.0.1" --ssl true`

Run scrapy with `PROXY_POOL`:

`PROXY_POOL=localhost:22999 scrapy crawl events -a page_slug=es/ibiza`
