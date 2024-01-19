import os
import glob
from datetime import datetime
import requests

def create_github_release(access_token, repo_owner, repo_name):
    tag_name = datetime.now().strftime("%d-%m-%Y")
    
    patch_file_path = next((f for f in glob.glob('revanced-patches*.jar') if os.path.isfile(f)), None)
    apk_file_path = next((f for f in glob.glob('youtube-revanced*.apk') if os.path.isfile(f)), None)

    # Only release with APK file
    if not apk_file_path:
        return

    # Check if the release with the same tag already exists
    existing_release = requests.get(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/tags/{tag_name}",
        headers={"Authorization": f"token {access_token}"}
    ).json()

    if "id" in existing_release:
        existing_release_id = existing_release["id"]

        # If the release exists, delete it
        requests.delete(
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/{existing_release_id}",
            headers={"Authorization": f"token {access_token}"}
        )

    # Create a new release
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release {tag_name}",
        "body": os.path.splitext(os.path.basename(patch_file_path))[0]
    }
    new_release = requests.post(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
        headers={"Authorization": f"token {access_token}", "Content-Type": "application/json"},
        json=release_data
    ).json()
    release_id = new_release["id"]

    # Upload APK file
    upload_url_apk = f"https://uploads.github.com/repos/{repo_owner}/{repo_name}/releases/{release_id}/assets?name={apk_file_path}"
    apk_file_content = open(apk_file_path, 'rb').read()

    response = requests.post(
        upload_url_apk,
        headers={"Authorization": f"token {access_token}", "Content-Type": "application/vnd.android.package-archive"},
        data=apk_file_content
    )
