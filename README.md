**YouTube Revanced** & **YouTube Music Revanced**

**Now this repository can build more sources and apps**

**Script auto change apk's source**

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
        "tag": "latest" // Use prerelease, dev or blank. blank is newest
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
  - From now, ReVanced use [Revanced GmsCore](https://github.com/revanced/gmscore) to work.
  - APK without **x86** and **x86_64**
  - Apps releases will be grouped by the name of json in the [./sources/](./sources)
  - Download APK at Releases

### Available at this repository
 - YouTube Revanced
 - YouTube Music Revanced
   > You can fork and add more sources and apps

## Download page
Assets fetch from latest release (included [Revanced GmsCore](https://github.com/revanced/gmscore))
  - Eng page: https://revanced-nonroot.pages.dev
  - Vi page: https://revanced-nonroot.vercel.app

### Setting Patches
 - Add and edit in [./patches/[name_of_app_json]-[name-of-source-json].txt](./patches/)  
 - **+ Patch_name** to include patch
 - **- Patch_name** to exclude patch 
