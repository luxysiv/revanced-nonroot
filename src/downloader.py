import json
import logging
import requests

from src import (
    youtube,
    session,
    version 
)

def download_resource(url: str, name: str) -> str:
    filepath = f"./{name}"

    with session.get(url, stream=True) as res:
        res.raise_for_status()

        total_size = int(res.headers.get('content-length', 0))
        downloaded_size = 0

        with open(filepath, "wb") as file:
            for chunk in res.iter_content(chunk_size=8192):
                file.write(chunk)
                downloaded_size += len(chunk)

        logging.info(
            f"URL: {url} [{downloaded_size}/{total_size}] -> {name}"
        )

    return filepath

def download_required():
    logging.info("Downloading required resources")
    downloaded_files = {}
    base_url = "https://api.github.com/repos/{}/{}/releases/{}"

    with open('./etc/config.json', 'r') as json_file:
        repos_info = json.load(json_file)

    for repo_info in repos_info: 
        
        if "name" in repo_info:
            continue
            
        try:
            url = base_url.format(repo_info['user'], repo_info['repo'], repo_info['tag'])
            assets = requests.get(url).json().get("assets", [])

            for asset in assets:
                filepath = download_resource(asset["browser_download_url"], asset["name"])
                downloaded_files[repo_info['repo'].replace("/", "")] = filepath

        except requests.exceptions.HTTPError as err:
            logging.error(f"Error downloading resources for {repo_info['user']}/{repo_info['repo']}: {err}")
            continue

    return downloaded_files

def download_apk():
    global version
    with open("./patches.json", "r") as patches_file:
        patches = json.load(patches_file)

        versions = set()
        for patch in patches:
            compatible_packages = patch.get("compatiblePackages")
            if compatible_packages and isinstance(compatible_packages, list):
                for package in compatible_packages:
                    if (
                        package.get("name") == "com.google.android.youtube" and
                        package.get("versions") is not None and
                        isinstance(package["versions"], list) and
                        package["versions"]
                    ):
                        versions.update(
                            map(
                                str.strip, package["versions"]
                            )
                        )
                        
        version = sorted(versions, reverse=True)[0] #1,2,3 to lower version
        
        download_page = youtube.get_download_page(version)
        download_link = youtube.extract_download_link(download_page)

        filename = f"youtube-v{version}.apk"
        
        return download_resource(download_link, filename)

