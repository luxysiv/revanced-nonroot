import json
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import os

# Create Chrome driver with headless options
def create_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass sandbox mode
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--remote-debugging-port=9222")  # Configure remote debugging
    chrome_options.add_argument("start-maximized")  # Maximize window
    chrome_options.add_argument("disable-infobars")  # Disable infobars
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument(f"user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Click on 'See more' button if necessary
def click_see_more(driver):
    try:
        see_more_button = driver.find_element(By.ID, "button-list-more")
        if see_more_button:
            logging.info("Clicking 'See more' to load more versions.")
            see_more_button.click()
    except NoSuchElementException:
        logging.info("No 'See more' button found, all versions are already loaded.")
        pass

# Get the latest version of the app
def get_latest_version(app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'

    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    url = f"https://{config['name']}.en.uptodown.com/android/versions"
    
    driver = create_chrome_driver()  # Create driver
    driver.get(url)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")  # Parse HTML from Selenium
    driver.quit()

    version_spans = soup.select('#versions-items-list .version')
    
    versions = [span.text.strip() for span in version_spans]
    highest_version = max(versions)
    
    return highest_version

# Get download link for a specific version
def get_download_link(version: str, app_name: str) -> str:
    conf_file_path = f'./apps/uptodown/{app_name}.json'

    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)
    
    url = f"https://{config['name']}.en.uptodown.com/android/versions"

    driver = create_chrome_driver()  # Create driver
    driver.get(url)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")

    while True:
        divs = soup.find_all("div", {"data-url": True})
        for div in divs:
            version_span = div.find("span", class_="version")
            if version_span and version_span.text.strip() == version:
                dl_url = div["data-url"]
                
                # Navigate to the version-specific download page
                logging.info(f"Found download page for version {version}, navigating to it...")
                driver.get(dl_url)
                time.sleep(2)  # Wait for the page to load

                # Parse the download page for the actual download link
                soup = BeautifulSoup(driver.page_source, "html.parser")
                download_button = soup.find('button', {'id': 'detail-download-button'})
                if download_button and download_button.get('data-url'):
                    data_url = download_button.get('data-url')
                    full_url = f"https://dw.uptodown.com/dwn/{data_url}"
                    driver.quit()
                    return full_url

        # If the "See more" button is available, click to load more versions
        click_see_more(driver)
        soup = BeautifulSoup(driver.page_source, "html.parser")

    driver.quit()
    return None
