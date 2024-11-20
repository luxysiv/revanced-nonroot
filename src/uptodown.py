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
    # Load configuration
    with open(f'./apps/uptodown/{app_name}.json', 'r') as file:
        config = json.load(file)

    base_url = f"https://{config['name']}.en.uptodown.com/android"
    response = scraper.get(f"{base_url}/versions")
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    data_code = soup.find('h1', id='detail-app-name')['data-code']

    page = 1
    while True:
        response = scraper.get(f"{base_url}/apps/{data_code}/versions/{page}")
        response.raise_for_status()
        version_data = response.json().get('data', [])
        
        for entry in version_data:
            if entry["version"] == version:
                version_page = scraper.get(f"{entry['versionURL']}-x")
                version_page.raise_for_status()
                content_size = len(version_page.content)
                logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
                soup = BeautifulSoup(version_page.content, "html.parser")
                download_url = soup.find('button', id='detail-download-button')['data-url']
                return f"https://dw.uptodown.com/dwn/{download_url}"
        
        if all(entry["version"] < version for entry in version_data):
            break
        page += 1

    return None
