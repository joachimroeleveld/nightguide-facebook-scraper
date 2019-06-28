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
 
E.g. `scrapy crawl events -a page_slug=nl/utrecht`
 
### Environment variables

Create `.env` under `/facebook_scraper`

**Variables:**

 - `FB_ACCOUNTS` 
 - `PROXY_POOL`
 - `NG_API_HOST`
 - `NG_API_TOKEN`
