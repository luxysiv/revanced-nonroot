import os
import re
import json

from src import (
    session,
    repository,
    github_token
)

def convert_title(text):
    pattern = re.compile(r'\b([a-z0-9]+(?:-[a-z0-9]+)*)\b', re.IGNORECASE)
    return pattern.sub(lambda match: match.group(1).replace('-', ' ').title(), text)

def extract_version(file):
    if file:
        base_name = os.path.splitext(os.path.basename(file))[0]
        match = re.search(r'(\d+\.\d+\.\d+(-[a-z]+\.\d+)?(-release\d*)?)', base_name)
        if match:
            return match.group(1)
    return 'unknown'

def create_github_release(app_name, source, download_files, apk_file):
    source_path = f'./sources/{source}.json'
    with open(source_path, 'r') as json_file:
        info = json.load(json_file)

    name = info[0].get("name", "")
    
    find_file = lambda prefix, ext: next(
        (file for file in download_files if file.startswith(prefix) and file.endswith(ext)),
        None
    )
    cli_file = find_file('./revanced-cli', '.jar')
    patch_file = find_file('./patches', '.rvp')

    patchver = extract_version(patch_file)
    cliver = extract_version(cli_file)
    tag_name = f"{name}-v{patchver}"

    if not apk_file:
        print("APK file not found, skipping release.")
        return

    existing_release = session.get(
        f"https://api.github.com/repos/{repository}/releases/tags/{tag_name}",
        headers={
            "Authorization": f"token {github_token}"
        }
    ).json()

    if "id" in existing_release:
        existing_release_id = existing_release["id"]

        existing_assets = existing_release.get('assets', [])
        for asset in existing_assets:
            if asset['name'] == os.path.basename(apk_file):
                asset_id = asset['id']
                delete_response = session.delete(
                    f"https://api.github.com/repos/{repository}/releases/assets/{asset_id}",
                    headers={
                        "Authorization": f"token {github_token}"
                    }
                )

    else:
        release_body = f"""\
# Release Notes

## Build Tools:
- **ReVanced Patches:** v{patchver}
- **ReVanced CLI:** v{cliver}

## Note:
**ReVanced GmsCore** is **necessary** to work. 
- Please **download** it from [HERE](https://github.com/revanced/gmscore/releases/latest).
        """

        name_from_json = convert_title(name)
        release_name = f"{name_from_json} v{patchver}"

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

        existing_release_id = new_release["id"]

    upload_url_apk = f"https://uploads.github.com/repos/{repository}/releases/{existing_release_id}/assets?name={os.path.basename(apk_file)}"
    with open(apk_file, 'rb') as apk_file:
        file_content = apk_file.read()

    response = session.post(
        upload_url_apk,
        headers={
            "Authorization": f"token {github_token}",
            "Content-Type": "application/vnd.android.package-archive"
        },
        data=file_content
    )
