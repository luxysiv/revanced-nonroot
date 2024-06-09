import json
import logging 

from src import scraper 
from bs4 import BeautifulSoup
      
def get_latest_version(app_name: str) -> str:
    conf_file_path = f'./apps/apkpure/{app_name}.json'   
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
    
    url = f"https://apkpure.net/{config['name']}/{config['package']}/versions"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    version_info = soup.find('div', class_='ver-top-down')

    if version_info:
        version = version_info['data-dt-version']
        if version:
            return version
            
    return None

def get_download_link(version: str, app_name: str) ->str:
    conf_file_path = f'./apps/apkpure/{app_name}.json'   
    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
    
    url = f"https://apkpure.net/{config['name']}/{config['package']}/download/{version}"

    response = scraper.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    download_link = soup.find(
        'a', href=lambda href: href and f'/APK/{config['package']}' in href
    )
    if download_link:
        return download_link['href']
    
    return None
        
    return None
