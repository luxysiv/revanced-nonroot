import os
import sys
import glob
import logging
import subprocess

from src import (
    downloader ,
    check ,
    release, 
    session, 
    github_access_token, 
    repository_name, 
    repository_owner
)

def run_build():
    download_files = downloader.download_required()
    script_repo_body = check.download_release_body(repository_owner, repository_name, github_access_token)
    downloaded_patch_file = next((f for f in os.listdir('.') if f.startswith('revanced-patches') and f.endswith('.jar')), None)
    downloaded_patch_file_name = os.path.splitext(os.path.basename(downloaded_patch_file))[0]
    if not script_repo_body or check.check_release_body(script_repo_body, downloaded_patch_file_name):
        input_apk_filepath = downloader.download_apk()
        exclude_patches = []
        include_patches = []

        with open('./etc/patches.txt', 'r') as patches_file:
            for line in patches_file:
                line = line.strip()
                if line.startswith('-'):
                    exclude_patches.append("--exclude")
                    exclude_patches.append(line[1:].strip())
                elif line.startswith('+'):
                    include_patches.append("--include")
                    include_patches.append(line[1:].strip())

        process = subprocess.Popen(
            [
                "java",
                "-jar",
                download_files["revanced-cli"],
                "patch",
                "-b",
                download_files["revanced-patches"],
                "-o",
                f"youtube-patch-v{downloader.version}.apk",
                "-m",
                download_files["revanced-integrations"],
                input_apk_filepath,
                *exclude_patches,
                *include_patches,
            ],
            stdout=subprocess.PIPE,
        )
    
        logging.info("Starting patch YouTube...")

        for line in iter(process.stdout.readline, b''):
            logging.info(line.decode("utf-8").strip())

        logging.info("Done")

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            logging.error("An error occurred while running the Java program")
            sys.exit(1)

        subprocess.run([
            max(glob.glob(os.path.join(os.environ.get('ANDROID_SDK_ROOT'), 'build-tools', '*/apksigner')), key=os.path.getctime),
            'sign',
            '--ks', './etc/public.jks',
            '--ks-pass', 'pass:public',
            '--key-pass', 'pass:public',
            '--ks-key-alias', 'public',
            '--in', f'youtube-patch-v{downloader.version}.apk',
            '--out', f'youtube-revanced-v{downloader.version}.apk'
        ])
    
        release.create_github_release(github_access_token, repository_owner, repository_name)
    else:
        logging.warning("Skipping build because patched")


if __name__ == "__main__":
    run_build()