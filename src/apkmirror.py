import re
import json
import logging 

from bs4 import BeautifulSoup
from src import base_url, scraper

def get_download_page(version: str, app_name: str) -> str:
    
    conf_file_path = f'./apps/apkmirror/{app_name}.json'   
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    criteria = [config['type'], config['arch'], config['dpi']]
    url = (f"{base_url}/apk/{config['org']}/{config['name']}/"
           f"{config['name']}-{version.replace('.', '-')}-release/")
    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")

    rows = soup.find_all('div', class_='table-row headerFont')
    for row in rows:
        row_text = row.get_text()
        if all(criterion in row_text for criterion in criteria):
            sub_url = row.find('a', class_='accent_color')
            if sub_url:
                return base_url + sub_url['href']
    return None

def extract_download_link(page: str) -> str:
    response = scraper.get(page)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")

    sub_url = soup.find('a', class_='downloadButton')
    if sub_url:
        download_page_url = base_url + sub_url['href']
        response = scraper.get(download_page_url)
        response.raise_for_status()
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
        soup = BeautifulSoup(response.content, "html.parser")

        sub_url = soup.select_one('a[rel="nofollow"]')
        if sub_url:
            return base_url +  sub_url['href']

    return None

def get_latest_version(app_name: str) -> str:
    
    conf_file_path = f'./apps/apkmirror/{app_name}.json'    
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
        
    url = f"{base_url}/uploads/?appcategory={config['name']}"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")

    app_rows = soup.find_all("div", class_="appRow")
    version_pattern = re.compile(r'\d+(\.\d+)*(-[a-zA-Z0-9]+(\.\d+)*)*')

    for row in app_rows:
        version_text = row.find("h5", class_="appRowTitle").a.text.strip()
        if "alpha" not in version_text.lower() and "beta" not in version_text.lower():
            match = version_pattern.search(version_text)
            if match:
                return match.group()

    return None
