import os
import logging
import cloudscraper

base_url = "https://www.apkmirror.com"
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'android',
        'desktop': False
    }
)

# Logging Level
logging.basicConfig(
  level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
# Global version
version = {}

github_access_token = os.getenv("GITHUB_TOKEN")
repository_owner = os.getenv("GITHUB_REPOSITORY_OWNER")
repository_name = os.getenv("GITHUB_REPOSITORY_NAME")
