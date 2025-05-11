import json
import logging
import subprocess
import os
import re
import cgi
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from src import (
    apkpure,
    version,
    session,
    uptodown,
    apkmirror
)

def extract_filename(response, fallback_url=None) -> str:
    # 1. Try Content-Disposition header
    cd = response.headers.get('content-disposition')
    if cd:
        _, params = cgi.parse_header(cd)
        filename = params.get('filename') or params.get('filename*')
        if filename:
            return unquote(filename)

    # 2. Try response-content-disposition from query string
    parsed = urlparse(response.url)
    query_params = parse_qs(parsed.query)
    rcd = query_params.get('response-content-disposition')
    if rcd:
        _, params = cgi.parse_header(unquote(rcd[0]))
        filename = params.get('filename') or params.get('filename*')
        if filename:
            return unquote(filename)

    # 3. Fallback to URL path
    path = urlparse(fallback_url or response.url).path
    return unquote(os.path.basename(path))


def download_resource(url: str, name: str = None) -> str:
    with session.get(url, stream=True) as res:
        res.raise_for_status()
        final_url = res.url

        # Determine filename
        if not name:
            name = extract_filename(res, fallback_url=final_url)

        filepath = f"./{name}"
        total_size = int(res.headers.get('content-length', 0))
        downloaded_size = 0

        with open(filepath, "wb") as file:
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)

        logging.info(
            f"URL: {final_url} [{downloaded_size}/{total_size}] -> \"{name}\" [1]"
        )

    return filepath

def download_required(source: str) -> list:
    downloaded_files = []
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
        response = session.get(url)
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
        assets = response.json()["assets"] or []

        for asset in assets:
            filepath = download_resource(asset["browser_download_url"])
            downloaded_files.append(filepath)

    return downloaded_files

def detect_github_link(base_url: str, user: str, repo: str, tag: str) -> str:
    if tag in ["", "dev", "prerelease"]:
        url = f"https://api.github.com/repos/{user}/{repo}/releases"
        response = session.get(url)
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
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

def normalize_version(version):
    parts = version.split('.')
    normalized = []
    for part in parts:
        match = re.match(r'(\d+)', part)
        if match:
            normalized.append(int(match.group(1)))
        else:
            normalized.append(0)
    return normalized

def get_highest_version(versions):
    if not versions:
        return None
    highest_version = versions[0]
    for v in versions[1:]:
        if normalize_version(v) > normalize_version(highest_version):
            highest_version = v
    return highest_version

def get_supported_version(package_name, cli, patches):
    output = subprocess.check_output([
        'java', '-jar', cli,
        'list-versions',
        '-f', f'{package_name}',
        patches
    ])
    output = output.decode('utf-8')
    versions = [
        line.split(' ')[0].strip()
        for line in output.splitlines()[2:]
        if 'Any' not in line and line.split(' ')[0].strip()
    ]
    if not versions:
        return None
    return get_highest_version(versions)

def download_platform(app_name: str, platform: str, cli: str, patches: str) -> tuple[str, str]:
    try:
        config_path = Path(f'./apps/{platform}/{app_name}.json')
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open() as json_file:
            config = json.load(json_file)

        ver = config['version'] or None
        if not ver:
            ver = get_supported_version(config['package'], cli, patches)

        platform_module = globals()[platform]
        if not ver:
            ver = platform_module.get_latest_version(app_name)

        download_link = platform_module.get_download_link(ver, app_name)
        filepath = download_resource(download_link)
        return filepath, ver

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None, None

def download_apkmirror(app_name: str, cli: str, patches: str) -> tuple[str, str]:
    return download_platform(app_name, "apkmirror", cli, patches)

def download_apkpure(app_name: str, cli: str, patches: str) -> tuple[str, str]:
    return download_platform(app_name, "apkpure", cli, patches)

def download_uptodown(app_name: str, cli: str, patches: str) -> tuple[str, str]:
    return download_platform(app_name, "uptodown", cli, patches)

def download_apkeditor() -> str:
    base_url = "https://api.github.com/repos/{}/{}/releases/latest"
    url = detect_github_link(base_url, "REAndroid", "APKEditor", "latest")
    response = session.get(url)
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    assets = response.json().get("assets", [])

    for asset in assets:
        if asset["name"].endswith(".jar"):
            return download_resource(asset["browser_download_url"])

    raise RuntimeError("APKEditor .jar file not found in the latest release")
