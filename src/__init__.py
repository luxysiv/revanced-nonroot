import os
import logging
import random
import requests

# --- Auto Generate User-Agent ---
os_platforms = {
    "Windows": [
        "Windows NT 10.0; Win64; x64",
        "Windows NT 11.0; Win64; x64",
        "Windows NT 10.0; WOW64"
    ],
    "macOS": [
        "Macintosh; Intel Mac OS X 13_5",
        "Macintosh; Apple M1 Mac OS X 13_5"
    ],
    "Linux": [
        "X11; Linux x86_64",
        "X11; Ubuntu; Linux x86_64"
    ],
    "Android": [
        "Linux; Android 14; Pixel 8 Pro",
        "Linux; Android 13; SM-G998B",
        "Linux; Android 12; SM-G991B",
        "Linux; Android 13; SM-S918B"
    ],
    "iOS": [
        "iPhone; CPU iPhone OS 17_5 like Mac OS X",
        "iPad; CPU OS 17_5 like Mac OS X"
    ]
}

browser_by_os = {
    "Windows": ["Chrome", "Firefox", "Edge", "Opera", "Vivaldi", "Brave"],
    "macOS": ["Chrome", "Firefox", "Safari", "Brave"],
    "Linux": ["Chrome", "Firefox", "Vivaldi", "Brave"],
    "Android": ["Chrome", "Firefox", "Samsung Browser", "Brave"],
    "iOS": ["Safari", "Chrome"]
}

browser_templates = {
    "Chrome": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36",
    "Edge": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36 Edg/{ver}",
    "Opera": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36 OPR/{ver}",
    "Vivaldi": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36 Vivaldi/{ver}",
    "Brave": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36 Brave/{ver}",
    "Firefox": "Mozilla/5.0 ({platform}; rv:{ver}) Gecko/20100101 Firefox/{ver}",
    "Samsung Browser": "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/{ver} Chrome/{ver} Safari/537.36",
    "Firefox Focus": "Mozilla/5.0 ({platform}; Mobile; rv:{ver}) Gecko/{ver} Firefox/{ver} Focus",
    "Firefox Klar": "Mozilla/5.0 ({platform}; Mobile; rv:{ver}) Gecko/{ver} Firefox/{ver} Klar",
    "Firefox Nightly": "Mozilla/5.0 ({platform}; Mobile; rv:{ver}) Gecko/{ver} Firefox/{ver} Nightly",
    "Safari": "Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{ver} Mobile/15E148 Safari/604.1"
}


def random_version(browser):
    if browser in ["Chrome", "Edge", "Opera", "Vivaldi", "Brave"]:
        return f"{random.randint(120, 126)}.0.{random.randint(6000, 6399)}.{random.randint(50, 99)}"
    elif browser == "Samsung Browser":
        return f"{random.randint(20, 23)}.0"
    elif "Firefox" in browser:
        return f"{random.randint(122, 126)}.{random.randint(0, 9)}"
    elif browser == "Safari":
        return f"{random.randint(16, 17)}.{random.randint(0, 6)}"
    else:
        return "1.0"


def generate_user_agent():
    os_name = random.choice(list(os_platforms.keys()))
    platform = random.choice(os_platforms[os_name])
    browser = random.choice(browser_by_os[os_name])
    version = random_version(browser)
    template = browser_templates[browser]
    return template.format(platform=platform, ver=version)

# --- Requests Session with Random User-Agent ---
session = requests.Session()
session.headers.update({
    'User-Agent': generate_user_agent()
})

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Env Vars
github_token = os.getenv('GITHUB_TOKEN')
repository = os.getenv('GITHUB_REPOSITORY')
endpoint_url = os.getenv('ENDPOINT_URL')
access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
bucket_name = os.getenv('BUCKET_NAME')

# APKmirror base url
base_url = "https://www.apkmirror.com"
