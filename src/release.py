import os
import re
import json

from src import (
    scraper,
    repository,
    github_token
)

def convert_title(text):
    pattern = re.compile(r'\b([a-z0-9]+(?:-[a-z0-9]+)*)\b', re.IGNORECASE)
    return pattern.sub(lambda match: match.group(1).replace('-', ' ').title(), text)

def extract_version(file_path):
    if file_path:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        match = re.search(r'(\d+\.\d+\.\d+(-[a-z]+\.\d+)?(-release\d*)?)', base_name)
        if match:
            return match.group(1)
    return 'unknown'

def create_github_release(app_name, source, download_files, apk_file_path):
    source_path = f'./sources/{source}.json'
    with open(source_path, 'r') as json_file:
        info = json.load(json_file)

    name = info[0].get("name", "")

    patch_file_path = download_files["revanced-patches"]
    integrations_file_path = download_files["revanced-integrations"]
    cli_file_path = download_files["revanced-cli"]

    patchver = extract_version(patch_file_path)
    integrationsver = extract_version(integrations_file_path)
    cliver = extract_version(cli_file_path)
    tag_name = f"{name}-v{patchver}"

    if not apk_file_path:
        print("APK file not found, skipping release.")
        return

    existing_release = scraper.get(
        f"https://api.github.com/repos/{repository}/releases/tags/{tag_name}",
        headers={
            "Authorization": f"token {github_token}"
        }
    ).json()

    if "id" in existing_release:
        existing_release_id = existing_release["id"]

        existing_assets = existing_release.get('assets', [])
        for asset in existing_assets:
            if asset['name'] == os.path.basename(apk_file_path):
                asset_id = asset['id']
                delete_response = scraper.delete(
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
- **ReVanced Integrations:** v{integrationsver}
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
        new_release = scraper.post(
            f"https://api.github.com/repos/{repository}/releases",
            headers={
                "Authorization": f"token {github_token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(release_data)
        ).json()

        existing_release_id = new_release["id"]

    upload_url_apk = f"https://uploads.github.com/repos/{repository}/releases/{existing_release_id}/assets?name={os.path.basename(apk_file_path)}"
    with open(apk_file_path, 'rb') as apk_file:
        apk_file_content = apk_file.read()

    response = scraper.post(
        upload_url_apk,
        headers={
            "Authorization": f"token {github_token}",
            "Content-Type": "application/vnd.android.package-archive"
        },
        data=apk_file_content
    )
