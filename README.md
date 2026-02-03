**Now, this repository can build more sources and apps.**

**Script auto change APK's source if download APK failure & merge if bundle**

**Files will be upload to R2 Cloudflare**

**Link's download below is R2. It's fast.**

### Download
  - Download page: https://revanced-nonroot.timie.workers.dev/
   > You can fork and add more sources and apps

### Usage 

 - Add sources patches at [./sources/](./sources)
 > Example usage:
 ```json
 [
    {
        "name": "revanced" # Used release 
    },
    {
        "user": "revanced",
        "repo": "revanced-cli",
        "tag": "latest" // Use prerelease, dev, blank or vx.x.x. blank is newest
    },
    {
        "user": "revanced",
        "repo": "revanced-patches",
        "tag": "latest" 
    },
    {
        "user": "revanced",
        "repo": "revanced-integrations",
        "tag": "latest"
    }
]
```
 - Add config APKmirror at [./apps/apkmirror/](./apps/apkmirror/)
 > Example usage:
 ```json
 {
    "org": "google-inc",
    "name": "youtube",
    "type": "APK", 
    "arch": "universal", //blank if use universal too
    "dpi": "nodpi",
    "package" : "com.google.android.youtube",
    "version" : "" // Set specific version if you want 
}
```
- Add config APKpure at [./apps/apkpure/](./apps/apkpure/)
 > Example usage:
 ```json
{
    "name": "youtube",
    "package" : "com.google.android.youtube",
    "version" : ""
}
```
- Add config uptodown at [./apps/uptodown/](./apps/uptodown/)
 > Example usage:
 ```json
{
    "name": "youtube",
    "package" : "com.google.android.youtube",
    "version" : ""
}
```
 - Controls apps to patch at [patch-config.json](patch-config.json)
 > Example usage:
 ```json
 {
  "patch_list": [
    { "app_name": "youtube", "source": "revanced" },
    { "app_name": "youtube", "source": "revanced-extended" },
    { "app_name": "name_of_app_json", "source": "name_of_source_json" }
  ]
}
```

### Latest release information
  - [Revanced](https://github.com/revanced/revanced-patches/releases/latest)
  - [Revanced Extended](https://github.com/inotia00/revanced-patches/releases/latest)

### Note
  - APK without **x86** and **x86_64**
  - If you want to Release on Github, go to [main.py](./src/__main__.py) edit like
```python
    release.create_github_release(name, revanced_patches, revanced_cli, signed_apk)
    # r2.upload(str(signed_apk), f"{app_name}/{signed_apk.name}")
```
  - Apps releases will be grouped by the name of json in the [./sources/](./sources)
  - Download APK at Releases

### Setting Patches
 - Add and edit in [./patches/[name_of_app_json]-[name-of-source-json].txt](./patches/)  
 - **+ Patch_name** to include patch
 - **- Patch_name** to exclude patch
