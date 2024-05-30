import json
import logging
import cloudscraper

from src import apkmirror, version

scraper = cloudscraper.create_scraper(
    browser={
        'custom': 'Mozilla/5.0'
    }
)
def download_resource(url: str, name: str) -> str:
    filepath = f"./{name}"

    with scraper.get(url, stream=True) as res:
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

def download_required(source: str) -> str:
    logging.info("Downloading required resources")
    downloaded_files = {}
    base_url = "https://api.github.com/repos/{}/{}/releases/{}"

    source_path = f'./sources/{source}.json'
    with open(source_path) as json_file:
        repos_info = json.load(json_file)

    for repo_info in repos_info:
        if "name" in repo_info:
            continue

        try:
            url = base_url.format(repo_info['user'], repo_info['repo'], repo_info['tag'])
            response = scraper.get(url)
            assets = response.json().get("assets", [])

            for asset in assets:
                if asset["name"].endswith(".asc"):
                    continue 
                filepath = download_resource(asset["browser_download_url"], asset["name"])
                downloaded_files[repo_info['repo'].replace("/", "")] = filepath

        except requests.exceptions.HTTPError as err:
            logging.error(f"Error downloading resources for {repo_info['user']}/{repo_info['repo']}: {err}")
            continue

    return downloaded_files

def download_apk(app_name: str) -> str:
    global version

    with open("./patches.json", "r") as patches_file:
        patches = json.load(patches_file)

    conf_file_path = f'./conf/{app_name}.json'

    with open(conf_file_path, 'r') as json_file:
        config = json.load(json_file)

    version = config['version']
    
    # If no version in config file, try to get it from patches.json
    if not version:
        versions = set()
        for patch in patches:
            compatible_packages = patch.get("compatiblePackages")
            if compatible_packages and isinstance(compatible_packages, list):
                for package in compatible_packages:
                    if (
                        package.get("name") == config['package'] and
                        package.get("versions") is not None and
                        isinstance(package["versions"], list) and
                        package["versions"]
                    ):
                        versions.update(
                            map(
                                str.strip, package["versions"]
                            )
                        )

        
        if versions:
            version = sorted(versions, reverse=True)[0]
    
    # If still no version, get the latest version from apkmirror
    if not version:
        version = apkmirror.get_latest_version(app_name)

    download_page = apkmirror.get_download_page(version, app_name)
    download_link = apkmirror.extract_download_link(download_page)

    filename = f"{app_name}-v{version}.apk"
    
    return download_resource(download_link, filename)
