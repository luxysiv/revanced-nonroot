import os
import random
import time
import requests
import logging 

user_agents = [
    # Chrome Windows/Mac/Linux
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36',
    
    # Firefox Windows/Mac/Linux
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
    
    # Safari Mac/iOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    
    # Edge/Opera
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36 Edg/125.0.2535.67',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36 OPR/91.0.4516.20',
    
    # Android
    'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Mobile Safari/537.36'
]

def generate_headers(user_agent):
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    platform = 'Windows'
    if 'Macintosh' in user_agent:
        platform = 'macOS'
    elif 'Linux' in user_agent and 'Android' not in user_agent:
        platform = 'Linux'
    elif 'Android' in user_agent or 'iPhone' in user_agent:
        platform = 'Mobile'

    if any(x in user_agent for x in ['Chrome', 'Edg', 'OPR']):
        headers.update({
            'Sec-Ch-Ua': f'"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?1' if platform == 'Mobile' else '?0',
            'Sec-Ch-Ua-Platform': f'"{platform}"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
        
        if 'Edg' in user_agent:
            headers['Sec-Ch-Ua'] = '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"'
        elif 'OPR' in user_agent:
            headers['Sec-Ch-Ua'] = '"Opera";v="91", "Chromium";v="125", "Not.A/Brand";v="24"'
    
    elif 'Firefox' in user_agent:
        headers.update({
            'DNT': '1',
            'TE': 'trailers',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    elif 'Safari' in user_agent:
        headers.update({
            'Referer': 'https://www.apple.com/',
            'X-Requested-With': 'XMLHttpRequest'
        })

    if platform == 'Mobile':
        headers.update({
            'Viewport-Width': str(random.choice([360, 375, 390, 412, 414])),
            'Device-Memory': str(random.choice([2, 4, 8]))
        })

    return headers

session = requests.Session()
user_agent = random.choice(user_agents)
headers = generate_headers(user_agent)
headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
session.headers.update(headers)
time.sleep(random.uniform(0.5, 2.0))

base_url = "https://www.apkmirror.com"

# Logging Level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

github_token = os.getenv('GITHUB_TOKEN')
repository = os.getenv('GITHUB_REPOSITORY')
endpoint_url = os.getenv('ENDPOINT_URL')
access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
bucket_name = os.getenv('BUCKET_NAME')
