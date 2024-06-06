import json
import logging

from src import (
    apkpure, 
    version, 
    scraper, 
    uptodown, 
    apkmirror 
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

def download_required(source: str) -> dict:
    downloaded_files = {}
    base_url = "https://api.github.com/repos/{}/{}/releases/{}"

    source_path = f'./sources/{source}.json'
    with open(source_path) as json_file:
        repos_info = json.load(json_file)

    for repo_info in repos_info:
        
        if "name" in repo_info:
            continue

        user = repo_info['user']
        repo = repo_info['repo']
        tag = repo_info['tag']

        url = detect_github_link(base_url, user, repo, tag)
        response = scraper.get(url)
        assets = response.json().get("assets", [])

        for asset in assets:
            if not asset["name"].endswith(".asc"):
                filepath = download_resource(asset["browser_download_url"], asset["name"])
                downloaded_files[repo_info['repo'].replace("/", "")] = filepath

    return downloaded_files


def detect_github_link(base_url: str, user: str, repo: str, tag: str) -> str:
    if tag in ["", "dev", "prerelease"]:
        url = f"https://api.github.com/repos/{user}/{repo}/releases"
        response = scraper.get(url)
        releases = response.json()

        if tag == "":
            latest_release = max(releases, key=lambda x: x['created_at'])
        elif tag == "dev":
            dev_releases = [release for release in releases if 'dev' in release['tag_name']]
            latest_release = max(dev_releases, key=lambda x: x['created_at'])
        else:
            pre_releases = [release for release in releases if release['prerelease']]
            latest_release = max(pre_releases, key=lambda x: x['created_at'])

        latest_tag_name = latest_release['tag_name']
        return base_url.format(user, repo, f"tags/{latest_tag_name}")
    else:
        return base_url.format(user, repo, tag)


def get_supported_version(package_name):
    with open("./patches.json", "r") as patches_file:
        patches = json.load(patches_file)
    versions = set()
    for patch in patches:
        compatible_packages = patch.get("compatiblePackages")
        if compatible_packages and isinstance(compatible_packages, list):
            for package in compatible_packages:
                if (
                    package.get("name") == package_name and
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
        return sorted(versions, reverse=True)[0]
    return None


def download_apkmirror(app_name: str) -> str:
    global version

    try:
        conf_file_path = f'./apps/apkmirror/{app_name}.json'

        with open(conf_file_path, 'r') as json_file:
            config = json.load(json_file)

        version = config['version']
        type = config['type']

        if type == 'BUNDLE':
            ext = 'apkm'
        elif type == 'APK':
            ext = 'apk'
        else:
            ext = 'apk'

        if not version:
            version = get_supported_version(config['package'])

        if not version:
            version = apkmirror.get_latest_version(app_name)

        download_page = apkmirror.get_download_page(version, app_name)
        download_link = apkmirror.extract_download_link(download_page)

        filename = f"{app_name}-v{version}.apk"
        
        return download_resource(download_link, filename)
    except Exception as e:
        return None


def download_apkpure(app_name: str) -> str:
    global version

    try:
        conf_file_path = f'./apps/apkpure/{app_name}.json'

        with open(conf_file_path, 'r') as json_file:
            config = json.load(json_file)

        version = config['version']

        if not version:
            version = get_supported_version(config['package'])

        if not version:
            version = apkpure.get_latest_version(app_name)

        download_link = apkpure.get_download_link(version, app_name)
        filename = f"{app_name}-v{version}.apk"
        
        return download_resource(download_link, filename)
    except Exception as e:
        return None


def download_uptodown(app_name: str) -> str:
    global version

    try:
        conf_file_path = f'./apps/uptodown/{app_name}.json'

        with open(conf_file_path, 'r') as json_file:
            config = json.load(json_file)

        version = config['version']

        if not version:
            version = get_supported_version(config['package'])

        if not version:
            version = uptodown.get_latest_version(app_name)

        download_link = uptodown.get_download_link(version, app_name)
        filename = f"{app_name}-v{version}.apk"
        
        return download_resource(download_link, filename)
    except Exception as e:
        return None
