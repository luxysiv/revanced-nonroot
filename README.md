**YouTube Revanced** & **YouTube Music Revanced**

**Now this repository can build more sources and apps**
 - Add sources patches at [./sources/](./sources)
 - Add apps to patch at [./conf/](./conf)
 - Format is json
 - Controls apps to patch at [.github/workflows/build.yml](.github/workflows/build.yml)

**Latest release information**
  - [Revanced](https://github.com/revanced/revanced-patches/releases/latest)
  - [Revanced Extended](https://github.com/inotia00/revanced-patches/releases/latest)

**Note**
  - From now, ReVanced use [Revanced GmsCore](https://github.com/revanced/gmscore) to work.
  - APK without **x86** and **x86_64**
  - Apps releases will be grouped by the name specified in the [./sources/](./sources) JSON
  - Download APK at Releases

**Download page** (Take from latest release) (included [Revanced GmsCore](https://github.com/revanced/gmscore))
  - Eng page: https://revanced-nonroot.pages.dev
  - Vi page: https://revanced-nonroot.vercel.app

**Setting Patches**
 - Edit in [./patches/[app_name]-[name-of-source-json].txt](./patches/)   
 - **+ Patch_name** to include patch
 - **- Patch_name** to exclude patch 
