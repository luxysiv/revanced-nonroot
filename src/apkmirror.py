import re
import json

from bs4 import BeautifulSoup
from src import base_url, scraper

def get_download_page(version: str, app_name: str) -> str:
    
    conf_file_path = f'./apps/apkmirror/{app_name}.json'   
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    keywords = [config['type'], config['arch'], config['dpi']]
    url = (f"{base_url}/apk/{config['org']}/{config['name']}/"
           f"{config['name']}-{version.replace('.', '-')}-release/")
    response = scraper.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    for href_content in soup.find_all('a', class_='accent_color'):
        parent = href_content.find_parent('div', class_='table-cell')
        if parent:
            infos = [parent.get_text(strip=True)] + [
                sib.get_text(strip=True) for sib in parent.find_next_siblings('div')
            ]
            if all(any(keyword in info for info in infos) for keyword in keywords):
                return base_url + href_content['href']

    return None

def extract_download_link(page: str) -> str:
    
    response = scraper.get(page)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    href_content = soup.find('a', class_='downloadButton')
    if href_content:
        download_page_url = base_url + href_content['href']
        response = scraper.get(download_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        href_content = soup.select_one('a[rel="nofollow"]')
        if href_content:
            return base_url + href_content['href']

    return None

def get_latest_version(app_name: str) -> str:
    
    conf_file_path = f'./apps/apkmirror/{app_name}.json'    
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
        
    url = f"{base_url}/uploads/?appcategory={config['name']}"

    response = scraper.get(url)
    response.raise_for_status()
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
