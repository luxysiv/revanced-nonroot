import os
import sys
import json
import glob
import logging
import subprocess

from src import (
    release,
    downloader,
    repository_name,
    repository_owner,
    github_access_token
)

def run_build(app_name: str, source: str) -> str:
    download_files = downloader.download_required(source)
    input_apk_filepath = downloader.download_apk(app_name)
    exclude_patches = []
    include_patches = []
    
    patches_path = f'./patches/{app_name}-{source}.txt'
    if os.path.exists(patches_path):
        with open(patches_path, 'r') as patches_file:
            for line in patches_file:
                line = line.strip()
                if line.startswith('-'):
                    exclude_patches.append("--exclude")
                    exclude_patches.append(line[1:].strip())
                elif line.startswith('+'):
                    include_patches.append("--include")
                    include_patches.append(line[1:].strip())

    libs_process = subprocess.Popen(
        [
            "zip",
            "--delete",
            input_apk_filepath,
            "lib/x86/*",
            "lib/x86_64/*",
        ],
        stdout=subprocess.DEVNULL,  
        stderr=subprocess.PIPE     
    )

    _, stderr = libs_process.communicate()
    libs_return_code = libs_process.returncode
        
    patch_process = subprocess.Popen(
        [
            "java",
            "-jar",
            download_files["revanced-cli"],
            "patch",
            "--patch-bundle",
            download_files["revanced-patches"],
            "--out",
            f"{app_name}-patch-v{downloader.version}.apk",
            "--merge",
            download_files["revanced-integrations"],
            input_apk_filepath,
            *exclude_patches,
            *include_patches,
        ],
        stdout=subprocess.PIPE,
    )

    for line in iter(patch_process.stdout.readline, b''):
        logging.info(line.decode("utf-8").strip())

    patch_process.stdout.close()
    patch_return_code = patch_process.wait()

    if patch_return_code != 0:
        logging.error("An error occurred while running the Java program")
        sys.exit(1)

    os.remove(input_apk_filepath)
    
    source_path = f'./sources/{source}.json'
    with open(source_path, 'r') as json_file:
        info = json.load(json_file)

    name = info[0].get("name", "")
        
    signing_process = subprocess.Popen(
        [
            max(glob.glob(os.path.join(os.environ.get('ANDROID_SDK_ROOT'), 'build-tools', '*/apksigner')), key=os.path.getctime),
            "sign",
            "--verbose",
            "--ks", "./etc/public.jks",
            "--ks-pass", "pass:public",
            "--key-pass", "pass:public",
            "--ks-key-alias", "public",
            "--in", f"{app_name}-patch-v{downloader.version}.apk",
            "--out", f"{app_name}-{name}-v{downloader.version}.apk"
        ],
        stdout=subprocess.PIPE,
    )

    for line in iter(signing_process.stdout.readline, b''):
        logging.info(line.decode("utf-8").strip())

    signing_process.stdout.close()
    signing_return_code = signing_process.wait()

    if signing_return_code != 0:
        logging.error("An error occurred while signing the APK")
        sys.exit(1)
    
    os.remove(f'{app_name}-patch-v{downloader.version}.apk')
    release.create_github_release(github_access_token, repository_owner, repository_name, app_name, source)

if __name__ == "__main__":
    app_name = os.getenv("APP_NAME")
    source = os.getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        sys.exit(1)

    run_build(app_name, source)
