import os
import logging
import requests

from src.colorlogs import ColoredLevelFormatter

# Session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0)"
    + " Gecko/20100101 Firefox/112.0"
})

# Logging Level
logging.getLogger().setLevel(logging.INFO)
formatter = ColoredLevelFormatter("%(asctime)s %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
console = logging.StreamHandler()
console.setFormatter(ColoredLevelFormatter("%(asctime)s %(message)s", datefmt='%Y-%m-%d %H:%M:%S'))
logger = logging.getLogger()
logger.addHandler(console)

# Global version
version = {}

github_access_token = os.getenv("GITHUB_TOKEN")
repository_owner = os.getenv("GITHUB_REPOSITORY_OWNER")
repository_name = os.getenv("GITHUB_REPOSITORY_NAME")
