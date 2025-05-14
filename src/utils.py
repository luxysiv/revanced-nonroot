import os
import re
import logging
import cgi
import json
from typing import List, Optional
from sys import exit
import subprocess
from urllib.parse import urlparse, unquote, parse_qs
from src import session

def find_file(files: list[str], prefix: str, suffix: str) -> str | None:
    return next(
        (f for f in files if f.startswith(prefix) and f.endswith(suffix)),
        None
    )

def find_apksigner() -> Optional[str]:
    sdk_root = os.environ.get('ANDROID_SDK_ROOT')
    if not sdk_root:
        logging.error("ANDROID_SDK_ROOT is not set")
        return None

    build_tools_path = os.path.join(sdk_root, 'build-tools')
    if not os.path.isdir(build_tools_path):
        logging.error("No build-tools directory found in ANDROID_SDK_ROOT")
        return None

    versions = sorted(os.listdir(build_tools_path), reverse=True)
    for version in versions:
        path = os.path.join(build_tools_path, version, 'apksigner')
        if os.path.isfile(path):
            return path

    logging.error("apksigner not found in any build-tools version")
    return None

def run_process(
    command: List[str],
    cwd: Optional[str] = None,
    capture: bool = False,
    stream: bool = False,
    silent: bool = False,
    check: bool = True,
    shell: bool = False
) -> Optional[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=shell
    )

    output_lines = []

    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                if not silent:
                    print(line.rstrip(), flush=True)
                if capture:
                    output_lines.append(line)
        process.stdout.close()
        return_code = process.wait()

        if check and return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)

        return ''.join(output_lines).strip() if capture else None

    except FileNotFoundError:
        print(f"Command not found: {command[0]}", flush=True)
        exit(1)
    except Exception as e:
        print(f"Error while running command: {e}", flush=True)
        exit(1)

def normalize_version(version: str) -> str:
    parts = version.split('.')
    normalized = []
    for part in parts:
        match = re.match(r'(\d+)', part)
        if match:
            normalized.append(int(match.group(1)))
        else:
            normalized.append(0)
    return normalized

def get_highest_version(versions: str) -> str:
    if not versions:
        return None
    highest_version = versions[0]
    for v in versions[1:]:
        if normalize_version(v) > normalize_version(highest_version):
            highest_version = v
    return highest_version
    
def get_supported_version(package_name: str, cli: str, patches: str) -> Optional[str]:
    output = run_process([
        'java', '-jar', cli,
        'list-versions',
        '-f', package_name,
        patches
    ], capture=True, silent=True)

    if not output:
        logging.warning("No output returned from list-versions command")
        return None

    lines = output.splitlines()
    if len(lines) <= 2:
        logging.warning("Output has no version lines")
        return None

    versions = []
    for line in lines[2:]:
        version, _, rest = line.partition(' ')
        version = version.strip()
        if version and 'Any' not in line:
            versions.append(version)

    if not versions:
        logging.warning("No supported versions found")
        return None

    return get_highest_version(versions)

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

def detect_github_release(user: str, repo: str, tag: str) -> dict:
    if tag == "latest":
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = session.get(url)
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
        return response.json()

    if tag in ["", "dev", "prerelease"]:
        url = f"https://api.github.com/repos/{user}/{repo}/releases"
        response = session.get(url)
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
        releases = response.json()

        if tag == "":
            release = max(releases, key=lambda x: x['created_at'])
        elif tag == "dev":
            devs = [r for r in releases if 'dev' in r['tag_name'].lower()]
            if not devs:
                raise ValueError(f"No dev release found for {user}/{repo}")
            release = max(devs, key=lambda x: x['created_at'])
        else:  # "prerelease"
            pres = [r for r in releases if r.get('prerelease')]
            if not pres:
                raise ValueError(f"No prerelease found for {user}/{repo}")
            release = max(pres, key=lambda x: x['created_at'])

        return release

    # Specific version tag
    url = f"https://api.github.com/repos/{user}/{repo}/releases/tags/{tag}"
    response = session.get(url)
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    return response.json()
