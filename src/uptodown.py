import json
import logging 

from src import scraper 
from bs4 import BeautifulSoup

def get_latest_version(app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    url = f"https://{config['name']}.en.uptodown.com/android/versions"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    version_spans = soup.select('#versions-items-list .version')
    versions = [span.text for span in version_spans]
    highest_version = max(versions)
    
    return highest_version

def get_download_link(version: str, app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
  
    url = f"https://{config['name']}.en.uptodown.com/android/versions"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    divs = soup.find_all("div", {"data-url": True})

    for div in divs:
        version_span = div.find("span", class_="version")
        if version_span and version_span.text == version:
            dl_page = div["data-url"]
            dl_url = dl_page.replace('/download/', '/post-download/')
            response = scraper.get(dl_url)
            response.raise_for_status()
            content_size = len(response.content)
            logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    
            soup = BeautifulSoup(response.content, "html.parser")
            post_download_divs = soup.find_all("div", class_="post-download")
            for post_div in post_download_divs:
                data_url = post_div.get("data-url")
                if data_url:
                    full_url = "https://dw.uptodown.com/dwn/" + data_url
                    return full_url

    return None
