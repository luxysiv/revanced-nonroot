import json
import logging
from pathlib import Path
from src import (
    utils,
    apkpure,
    session,
    uptodown,
    apkmirror
)

def download_resource(url: str, name: str = None) -> str:
    with session.get(url, stream=True) as res:
        res.raise_for_status()
        final_url = res.url

        # Determine filename
        if not name:
            name = utils.extract_filename(res, fallback_url=final_url)

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
    source_path = f'./sources/{source}.json'

    with open(source_path) as json_file:
        repos_info = json.load(json_file)

    for repo_info in repos_info:
        if "name" in repo_info:
            continue

        user = repo_info['user']
        repo = repo_info['repo']
        tag = repo_info['tag']

        release = utils.detect_github_release(user, repo, tag)
        for asset in release.get("assets", []):
            filepath = download_resource(asset["browser_download_url"])
            downloaded_files.append(filepath)

    return downloaded_files

def download_platform(app_name: str, platform: str, cli: str, patches: str) -> tuple[str, str]:
    try:
        config_path = Path(f'./apps/{platform}/{app_name}.json')
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open() as json_file:
            config = json.load(json_file)

        ver = config['version'] or None
        if not ver:
            ver = utils.get_supported_version(config['package'], cli, patches)

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
    release = utils.detect_github_release("REAndroid", "APKEditor", "latest")
    assets = release.get("assets", [])

    for asset in assets:
        if asset["name"].startswith("APKEditor") and asset["name"].endswith(".jar"):
            return download_resource(asset["browser_download_url"])

    raise RuntimeError("APKEditor .jar file not found in the latest release")
