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
    version = None
    for method in download_methods:
        input_apk_filepath, version = method(app_name, revanced_cli, revanced_patches)
        if input_apk_filepath:
            break

    if not input_apk_filepath:
        logging.error("Failed to download APK from all sources")
        exit(1)

    if not input_apk_filepath.endswith(".apk"):
        logging.warning("Input file is not .apk, using APKEditor to merge")
        apk_editor_jar = downloader.download_apkeditor()

        subprocess.run(
            ["java", "-jar", apk_editor_jar, "m", "-i", input_apk_filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        apk_filename = next((f for f in glob.glob("*_merged.apk")), None)

        if not apk_filename or not os.path.exists(apk_filename):
            logging.error("Merged APK file not found")
            exit(1)

        input_apk_filepath = apk_filename
        logging.info(f"Merged APK file detected: {input_apk_filepath}")

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

    subprocess.run(
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

    with open(f'./sources/{source}.json', 'r') as json_file:
        info = json.load(json_file)
    name = info[0].get("name", "")

    output_apk_filepath = f"{app_name}-patch-v{version}.apk"

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
        logging.error("An error occurred while patching the APK")
        sys.exit(1)

    os.remove(input_apk_filepath)

    signed_apk_filepath = f"{app_name}-{name}-v{version}.apk"

    signing_process = subprocess.Popen(
        [
            max(glob.glob(os.path.join(os.environ.get('ANDROID_SDK_ROOT'), 'build-tools', '*/apksigner')), key=os.path.getctime),
            "sign",
            "--verbose",
            "--ks", "./keystore/public.jks",
            "--ks-pass", "pass:public",
            "--key-pass", "pass:public",
            "--ks-key-alias", "public",
            "--in", output_apk_filepath,
            "--out", signed_apk_filepath
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

    os.remove(output_apk_filepath)
    # release.create_github_release(app_name, source, download_files, signed_apk_filepath)

    key = f"{app_name}/{signed_apk_filepath}"
    r2.upload(signed_apk_filepath, key)

if __name__ == "__main__":
    app_name = os.getenv("APP_NAME")
    source = os.getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        sys.exit(1)

    run_build(app_name, source)
