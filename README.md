# facebook-scraper

## Deployment

Build egg:
`scrapyd-deploy --build-egg output.egg`

Upload egg to Spiderkeeper

## Configuration

### Google auth

`facebook-scraper-sa` kubernetes secret has to contain Google application credentials.

### spider arguments

 - `page_slug` (required)
 - `without_images`
 - `event_page_depth`
 - `venue_id` or `venue_ids`
 - `event_ids` (required to also set `venue_id`)
 
E.g. `scrapy crawl events -a page_slug=nl/utrecht`
 
### Environment variables

Create `.env` under `/facebook_scraper`

**Variables:**

 - `FB_ACCOUNTS` 
 - `PROXY_POOL=ip:port:un:pw`
 - `NG_API_HOST`
 - `NG_API_TOKEN`


## Luminati proxy

Start proxy

`docker run -p 22999:22999 -p 24000:24000 luminati/luminati-proxy luminati --www_whitelist_ips "172.17.0.1" --ssl true`

Run scrapy with `PROXY_POOL`:

`PROXY_POOL=localhost:22999 scrapy crawl events -a page_slug=es/ibiza`