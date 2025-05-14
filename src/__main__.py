import os
import sys
import json
import glob
import logging
from sys import exit
from src import (
    r2,
    utils,
    release,
    downloader
)

def run_build(app_name: str, source: str) -> str:
    download_files = downloader.download_required(source)
    find_file = lambda prefix, ext: next(
        (f for f in download_files if f.startswith(prefix) and f.endswith(ext)),
        None
    )

    revanced_cli = find_file('./revanced-cli', '.jar')
    revanced_patches = find_file('./patches', '.rvp')

    download_methods = [
        downloader.download_apkmirror,
        downloader.download_uptodown,
        downloader.download_apkpure
    ]

    input_apk = None
    version = None
    for method in download_methods:
        input_apk, version = method(app_name, revanced_cli, revanced_patches)
        if input_apk:
            break

    if not input_apk:
        logging.error("Failed to download APK from all sources")
        exit(1)

    if not input_apk.endswith(".apk"):
        logging.warning("Input file is not .apk, using APKEditor to merge")
        apk_editor = downloader.download_apkeditor()

        utils.run_process([
            "java", "-jar", apk_editor, "m", "-i", input_apk
        ], silent=True)

        os.remove(input_apk)
        apk_filename = next((f for f in glob.glob("*_merged.apk")), None)

        if not apk_filename or not os.path.exists(apk_filename):
            logging.error("Merged APK file not found")
            exit(1)

        input_apk = apk_filename
        logging.info(f"Merged APK file detected: {input_apk}")

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

    utils.run_process([
        "zip", "--delete", input_apk, "lib/x86/*", "lib/x86_64/*"
    ], silent=True, check=False)

    with open(f'./sources/{source}.json', 'r') as json_file:
        info = json.load(json_file)
    name = info[0].get("name", "")

    output_apk = f"{app_name}-patch-v{version}.apk"

    utils.run_process([
        "java", "-jar", revanced_cli,
        "patch", "--patches", revanced_patches,
        "--out", output_apk, input_apk,
        *exclude_patches, *include_patches
    ], stream=True)

    os.remove(input_apk)
    signed_apk = f"{app_name}-{name}-v{version}.apk"

    apksigner = utils.find_apksigner()
    if not apksigner:
        exit(1)

    utils.run_process([
        apksigner, "sign", "--verbose",
        "--ks", "./keystore/public.jks",
        "--ks-pass", "pass:public",
        "--key-pass", "pass:public",
        "--ks-key-alias", "public",
        "--in", output_apk, "--out", signed_apk
    ], stream=True)

    os.remove(output_apk)
    # release.create_github_release(app_name, source, download_files, signed_apk)
    r2.upload(signed_apk, f"{app_name}/{signed_apk}")

if __name__ == "__main__":
    app_name = os.getenv("APP_NAME")
    source = os.getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        sys.exit(1)

    run_build(app_name, source)
