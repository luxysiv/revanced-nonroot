import json
import logging
from sys import exit
from pathlib import Path
from collections import defaultdict
from src import (
    r2,
    utils,
    release,
    downloader
)

def group_apps_by_source(patch_list):
    grouped = defaultdict(list)
    for app in patch_list:
        grouped[app['source']].append(app['app_name'])
    return grouped

def download_shared_resources(source):
    download_files, name = downloader.download_required(source)
    revanced_cli = utils.find_file(download_files, 'revanced-cli', '.jar')
    revanced_patches = utils.find_file(download_files, 'patches', '.rvp')
    return revanced_cli, revanced_patches, name

def run_build(app_name: str, source: str, revanced_cli: Path, revanced_patches: Path, name: str) -> str:
    download_methods = [
        downloader.download_apkmirror,
        downloader.download_apkpure,
        downloader.download_uptodown
    ]

    input_apk = None
    version = None
    for method in download_methods:
        input_apk, version = method(app_name, revanced_cli, revanced_patches)
        if input_apk:
            break

    if input_apk.suffix != ".apk":
        logging.warning("Input file is not .apk, using APKEditor to merge")
        apk_editor = downloader.download_apkeditor()

        merged_apk = input_apk.with_suffix(".apk")
        utils.run_process([
            "java", "-jar", apk_editor, "m",
            "-i", str(input_apk),
            "-o", str(merged_apk)
        ], silent=True)

        input_apk.unlink(missing_ok=True)
        if not merged_apk.exists():
            logging.error("Merged APK file not found")
            exit(1)

        input_apk = merged_apk
        logging.info(f"Merged APK file generated: {input_apk}")

    exclude_patches = []
    include_patches = []
    patches_path = Path("patches") / f"{app_name}-{source}.txt"
    if patches_path.exists():
        with patches_path.open('r') as patches_file:
            for line in patches_file:
                line = line.strip()
                if line.startswith('-'):
                    exclude_patches.extend(["-d", line[1:].strip()])
                elif line.startswith('+'):
                    include_patches.extend(["-e", line[1:].strip()])

    utils.run_process([
        "zip", "--delete", str(input_apk), "lib/x86/*", "lib/x86_64/*"
    ], silent=True, check=False)

    output_apk = Path(f"{app_name}-patch-v{version}.apk")
    utils.run_process([
        "java", "-jar", str(revanced_cli),
        "patch", "--patches", str(revanced_patches),
        "--out", str(output_apk), str(input_apk),
        *exclude_patches, *include_patches
    ], stream=True)

    input_apk.unlink(missing_ok=True)

    signed_apk = Path(f"{app_name}-{name}-v{version}.apk")
    apksigner = utils.find_apksigner()
    if not apksigner:
        exit(1)

    utils.run_process([
        str(apksigner), "sign", "--verbose",
        "--ks", "keystore/public.jks",
        "--ks-pass", "pass:public",
        "--key-pass", "pass:public",
        "--ks-key-alias", "public",
        "--in", str(output_apk), "--out", str(signed_apk)
    ], stream=True)

    output_apk.unlink(missing_ok=True)
    
    # release.create_github_release(name, revanced_patches, revanced_cli, signed_apk)
    r2.upload(str(signed_apk), f"{app_name}/{signed_apk.name}")
    
    signed_apk.unlink(missing_ok=True)
    
if __name__ == "__main__":
    source_ = Path("patch-config.json")
    with source_.open() as json_file:
        config = json.load(json_file)

    patch_list = config['patch_list']
    if not patch_list:
        logging.error("No apps to patch in config")
        exit(1)

    grouped_apps = group_apps_by_source(patch_list)
    apk_editor_downloaded = False

    for source, app_names in grouped_apps.items():
        logging.info(f"Processing source: {source}")
        try:
            revanced_cli, revanced_patches, name = download_shared_resources(source)
            
            for app_name in app_names:
                logging.info(f"Patching {app_name} from {source}")
                try:
                    run_build(app_name, source, revanced_cli, revanced_patches, name)
                except Exception as e:
                    logging.error(f"Failed to patch {app_name}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Failed to process source {source}: {e}")
            continue
