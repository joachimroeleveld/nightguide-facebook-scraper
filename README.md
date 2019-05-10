# facebook-scraper

## Deployment

Build egg:
`scrapyd-deploy --build-egg output.egg`

Upload egg to Spiderkeeper

## Configuration

### spider arguments

 - `city` (required)
 - `country` (required)
 
E.g. `scrapy crawl events -a country=NL`
 
### Environment variables

 - `PROXY_POOL`
 - `NG_API_HOST`
 - `NG_API_TOKEN`
