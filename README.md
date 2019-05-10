# facebook-scraper

## Deployment

Build egg:
`scrapyd-deploy --build-egg output.egg`

Upload egg to Spiderkeeper

## Configuration

### spider arguments

 - `city`
 - `country`
 - `req_items`
 
E.g. `scrapy crawl events -a req_items=1`
 
### Environment variables

 - `PROXY_POOL`
 - `NG_API_HOST`
 - `NG_API_TOKEN`
