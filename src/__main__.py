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
    downloader
)

def run_build(app_name: str, source: str) -> str:
    download_files = downloader.download_required(source)
    input_apk_filepath = downloader.download_apkmirror(app_name)
    if not input_apk_filepath:
        input_apk_filepath = downloader.download_uptodown(app_name)
    if not input_apk_filepath:
        input_apk_filepath = downloader.download_apkpure(app_name)
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

    source_path = f'./sources/{source}.json'
    with open(source_path, 'r') as json_file:
        info = json.load(json_file)

    name = info[0].get("name", "")

    output_apk_filepath = f"{app_name}-{name}-v{downloader.version}.apk"

    revanced-cli = next(
        filter(
            lambda file: file.endswith('.jar'), download_files['revanced-cli']
        )
    )
    revanced-patches = next(
        filter(
            lambda file: file.endswith('.jar'), download_files['revanced-patches']
        )
    )
    revanced-integrations = next(
        filter(
            lambda file: file.endswith('.apk'), download_files['revanced-integrations']
        )
    )
    
    patch_process = subprocess.Popen(
        [
            "java",
            "-jar",
            revanced-cli,
            "patch",
            "--patch-bundle",
            revanced-patches,
            "--out",
            output_apk_filepath,
            "--merge",
            revanced-integrations,
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

if __name__ == "__main__":
    app_name = os.getenv("APP_NAME")
    source = os.getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        sys.exit(1)

    run_build(app_name, source)
