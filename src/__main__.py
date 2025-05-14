import os
import sys
import json
import glob
import logging
import subprocess
from typing import List, Optional
from sys import exit
from src import (
    r2,
    release,
    downloader
)

def run_process(
    command: List[str],
    cwd: Optional[str] = None,
    capture_output: bool = False,
    capture_stderr: bool = False,
    silent: bool = False,
    check: bool = True,
    shell: bool = False,
    stream: bool = False
) -> Optional[str | tuple[str, str] | int]:
    if stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=shell
        )
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip(), flush=True)
        process.stdout.close()
        return process.wait()
    else:
        stdout_opt = subprocess.PIPE if capture_output else (subprocess.DEVNULL if silent else None)
        if capture_stderr:
            stderr_opt = subprocess.PIPE
        elif capture_output:
            stderr_opt = subprocess.STDOUT
        else:
            stderr_opt = subprocess.DEVNULL if silent else None

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=stdout_opt,
                stderr=stderr_opt,
                text=True,
                shell=shell
            )
            if capture_output and capture_stderr:
                return result.stdout.strip(), result.stderr.strip()
            elif capture_output:
                return result.stdout.strip()
            elif result.returncode != 0 and check:
                print(f"Command failed: {' '.join(command)}", flush=True)
                if result.stderr:
                    print(result.stderr.strip(), flush=True)
                exit(result.returncode)
            return result.returncode
        except FileNotFoundError:
            print(f"Command not found: {command[0]}", flush=True)
            exit(1)

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

        run_process(["java", "-jar", apk_editor, "m", "-i", input_apk], silent=True)

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

    run_process([
        "zip",
        "--delete",
        input_apk,
        "lib/x86/*",
        "lib/x86_64/*"
    ], silent=True, check=False)

    with open(f'./sources/{source}.json', 'r') as json_file:
        info = json.load(json_file)
    name = info[0].get("name", "")

    output_apk = f"{app_name}-patch-v{version}.apk"

    run_process([
        "java",
        "-jar",
        revanced_cli,
        "patch",
        "--patches",
        revanced_patches,
        "--out",
        output_apk,
        input_apk,
        *exclude_patches,
        *include_patches
    ], stream=True)

    os.remove(input_apk)
    signed_apk = f"{app_name}-{name}-v{version}.apk"

    apksigner_path = max(
        glob.glob(os.path.join(os.environ.get('ANDROID_SDK_ROOT'), 'build-tools', '*/apksigner')),
        key=os.path.getctime
    )

    run_process([
        apksigner_path,
        "sign",
        "--verbose",
        "--ks", "./keystore/public.jks",
        "--ks-pass", "pass:public",
        "--key-pass", "pass:public",
        "--ks-key-alias", "public",
        "--in", output_apk,
        "--out", signed_apk
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
