import json
import glob
import logging
from sys import exit
from pathlib import Path
from os import getenv
from src import (
    r2,
    utils,
    release,
    downloader
)

def run_build(app_name: str, source: str) -> str:
    download_files, name = downloader.download_required(source)
    
    revanced_cli = utils.find_file(download_files, './revanced-cli', '.jar')
    revanced_patches = utils.find_file(1download_files, './patches', '.rvp')

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
    elif not input_apk.endswith(".apk"):
        logging.warning("Input file is not .apk, using APKEditor to merge")
        apk_editor = downloader.download_apkeditor()
        utils.run_process([
            "java", "-jar", apk_editor, "m", "-i", input_apk
        ], silent=True)

        Path(input_apk).unlink(missing_ok=True)
        merged_apk = next((Path(f) for f in glob.glob("*_merged.apk")), None)

        if not merged_apk or not merged_apk.exists():
            logging.error("Merged APK file not found")
            exit(1)

        input_apk = str(merged_apk)
        logging.info(f"Merged APK file detected: {input_apk}")

    exclude_patches = []
    include_patches = []

    patches_path = Path(f'./patches/{app_name}-{source}.txt')
    if patches_path.exists():
        with patches_path.open('r') as patches_file:
            for line in patches_file:
                line = line.strip()
                if line.startswith('-'):
                    exclude_patches.extend(["-d", line[1:].strip()])
                elif line.startswith('+'):
                    include_patches.extend(["-e", line[1:].strip()])

    utils.run_process([
        "zip", "--delete", input_apk, "lib/x86/*", "lib/x86_64/*"
    ], silent=True, check=False)

    output_apk = Path(f"{app_name}-patch-v{version}.apk")

    utils.run_process([
        "java", "-jar", revanced_cli,
        "patch", "--patches", revanced_patches,
        "--out", str(output_apk), input_apk,
        *exclude_patches, *include_patches
    ], stream=True)

    Path(input_apk).unlink(missing_ok=True)

    signed_apk = Path(f"{app_name}-{name}-v{version}.apk")

    apksigner = utils.find_apksigner()
    if not apksigner:
        exit(1)

    utils.run_process([
        apksigner, "sign", "--verbose",
        "--ks", "./keystore/public.jks",
        "--ks-pass", "pass:public",
        "--key-pass", "pass:public",
        "--ks-key-alias", "public",
        "--in", str(output_apk), "--out", str(signed_apk)
    ], stream=True)

    output_apk.unlink(missing_ok=True)
    # release.create_github_release(name, revanced_patches, revanced_cli, signed_apk)
    r2.upload(str(signed_apk), f"{app_name}/{signed_apk.name}")

if __name__ == "__main__":
    app_name = getenv("APP_NAME")
    source = getenv("SOURCE")

    if not app_name or not source:
        logging.error("APP_NAME and SOURCE environment variables must be set")
        exit(1)

    run_build(app_name, source)
