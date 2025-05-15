import re
import json
from sys import exit
from pathlib import Path

from src import (
    session,
    repository,
    github_token
)

def convert_title(text):
    if not text or not isinstance(text, str):
        return text
    return re.sub(
        r'\b([a-z0-9]+(?:-[a-z0-9]+)*)\b',
        lambda m: m.group(1).replace('-', ' ').title(),
        text,
        flags=re.IGNORECASE
    )

def extract_version(file_path):
    if not file_path:
        return 'unknown'
    path = Path(file_path)
    base_name = path.stem
    match = re.search(r'(\d+\.\d+\.\d+(-[a-z]+\.\d+)?(-release\d*)?)', base_name)
    return match.group(1) if match else 'unknown'

def create_github_release(name, patches_name, cli_name, apk_file_path):
    patchver = extract_version(patches_name)
    cliver = extract_version(cli_name)
    tag_name = f"{name}-v{patchver}"

    apk_path = Path(apk_file_path)
    if not apk_path.exists():
        exit(1)

    # Step 1: Check for existing release with the exact tag name
    existing_release = session.get(
        f"https://api.github.com/repos/{repository}/releases/tags/{tag_name}",
        headers={"Authorization": f"token {github_token}"}
    ).json()

    existing_release_id = existing_release.get("id")

    # Step 2: Delete assets if the release exists and has the same APK
    if existing_release_id:
        for asset in existing_release.get('assets', []):
            if asset['name'] == apk_path.name:
                session.delete(
                    f"https://api.github.com/repos/{repository}/releases/assets/{asset['id']}",
                    headers={"Authorization": f"token {github_token}"}
                )

    # Step 3: Delete old releases with the same base name and matching version suffix
    releases = session.get(
        f"https://api.github.com/repos/{repository}/releases",
        headers={"Authorization": f"token {github_token}"}
    ).json()

    suffix_match = re.search(r'(-[a-z]+\.\d+)$', patchver)
    current_suffix = suffix_match.group(1) if suffix_match else ''

    for release in releases:
        release_tag = release['tag_name']
        if (
            release_tag.startswith(f"{name}-v")
            and release_tag != tag_name
            and release['id'] != existing_release_id
        ):
            old_version = release_tag[len(name) + 2:]
            old_suffix_match = re.search(r'(-[a-z]+\.\d+)$', old_version)
            old_suffix = old_suffix_match.group(1) if old_suffix_match else ''

            if old_suffix == current_suffix:
                old_numeric = re.sub(r'(-[a-z]+\.\d+)?(-release\d*)?$', '', old_version)
                current_numeric = re.sub(r'(-[a-z]+\.\d+)?(-release\d*)?$', '', patchver)
                if old_numeric < current_numeric:
                    session.delete(
                        f"https://api.github.com/repos/{repository}/releases/{release['id']}",
                        headers={"Authorization": f"token {github_token}"}
                    )

    # Step 4: Create new release if it doesn't exist
    if not existing_release_id:
        release_body = f"""\
# Release Notes

## Build Tools:
- **ReVanced Patches:** v{patchver}
- **ReVanced CLI:** v{cliver}

## Note:
**ReVanced GmsCore** is **necessary** to work. 
- Please **download** it from [HERE](https://github.com/revanced/gmscore/releases/latest).
"""
        release_name = f"{convert_title(name)} v{patchver}"
        release_data = {
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": release_name,
            "body": release_body
        }
        new_release = session.post(
            f"https://api.github.com/repos/{repository}/releases",
            headers={
                "Authorization": f"token {github_token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(release_data)
        ).json()
        existing_release_id = new_release.get("id")

    # Step 5: Upload APK
    upload_url_apk = f"https://uploads.github.com/repos/{repository}/releases/{existing_release_id}/assets?name={apk_path.name}"
    with apk_path.open('rb') as apk_file:
        session.post(
            upload_url_apk,
            headers={
                "Authorization": f"token {github_token}",
                "Content-Type": "application/vnd.android.package-archive"
            },
            data=apk_file.read()
    )
