import os
import sys
import json
import glob
import logging
import subprocess
from sys import exit
from src import (
    r2,
    release,
    telegram,
    downloader
)

def run_build(app_name: str, source: str) -> str:
    download_files = downloader.download_required(source)
    find_file = lambda prefix, ext: next(
        (file for file in download_files if file.startswith(prefix) and file.endswith(ext)),
        None
       )

    revanced_cli = find_file('./revanced-cli', '.jar')
    revanced_patches = find_file('./patches', '.rvp')
    
    download_methods = [
        downloader.download_apkmirror,
        downloader.download_uptodown,
        downloader.download_apkpure
    ]

    input_apk_filepath = None
    for method in download_methods:
        input_apk_filepath = method(app_name, revanced_cli, revanced_patches)
        if input_apk_filepath:
            break

    if not input_apk_filepath:
        exit(0)
        
    exclude_patches = []
    include_patches = []

    patches_path = f'./patches/{app_name}-{source}.txt'
    if os.path.exists(patches_path):
        with open(patches_path, 'r') as patches_file:
            for line in patches_file:
                line = line.strip()
                if line.startswith('-'):
                    exclude_patches.append("-d")
                    exclude_patches.append(line[1:].strip())
                elif line.startswith('+'):
                    include_patches.append("-e")
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

    source_path = f'./sources/{source}.json'
    with open(source_path, 'r') as json_file:
        info = json.load(json_file)

    name = info[0].get("name", "")

    output_apk_filepath = f"{app_name}-{name}-v{downloader.version}.apk"
    
    patch_process = subprocess.Popen(
        [
            "java",
            "-jar",
            revanced_cli,
            "patch",
            "--patches",
            revanced_patches,
            "--out",
            output_apk_filepath,
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


    # release.create_github_release(app_name, source, download_files, output_apk_filepath)
    
    key = f"{app_name}/{output_apk_filepath}"
    r2.upload(output_apk_filepath, key)
    
    telegram.upload_file_to_telegram(output_apk_filepath)

if __name__ == "__main__":
    app_name = os.getenv("APP_NAME")
    source = os.getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        sys.exit(1)

    run_build(app_name, source)
