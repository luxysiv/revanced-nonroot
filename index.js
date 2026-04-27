const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const { downloadLatestGithubAsset } = require("./lib/github");
const { extractYoutubeVersions, pickLatestVersion } = require("./lib/versions");
const { downloadApk } = require("./lib/apkmirror");
const { downloadFromUptodown } = require("./lib/uptodown");
const { patchApk } = require("./lib/patcher");
const { uploadApkRelease } = require("./lib/release");

(async () => {
  try {
    console.log("🚀 START\n");

    // 1. Download Morphe CLI
    console.log("🌐 FETCH: morphe-cli (GitHub)");
    const cli = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-cli",
      match: (n) => n.includes("cli") && n.endsWith(".jar"),
    });
    console.log("📦 CLI:", cli);

    // 2. Download patches
    console.log("🌐 FETCH: morphe-patches (GitHub)");
    const patches = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-patches",
      match: (n) => n.endsWith(".mpp"),
    });
    console.log("📦 PATCHES:", patches);

    // 3. Extract versions
    console.log("⬇️ Extract versions...");
    const output = execSync(`
      java -jar "${cli}" list-patches \
        --patches="${patches}" \
        --filter-package-name com.google.android.youtube \
        --with-versions
    `).toString();

    const versions = extractYoutubeVersions(output);
    const selectedVersion = pickLatestVersion(versions);

    if (!selectedVersion) throw new Error("No valid version found");

    console.log("➡️ TARGET:", selectedVersion);

    // 4. Download APK (with fallback)
    let apkPath;

    try {
      console.log("🌐 SOURCE: APKMirror");
      apkPath = await downloadApk(selectedVersion);
    } catch (apkMirrorError) {
      console.log("❌ APKMIRROR FAIL:", apkMirrorError.message);

      console.log("🔁 FALLBACK: Uptodown");

      try {
        console.log("🌐 SOURCE: Uptodown");
        apkPath = await downloadFromUptodown(selectedVersion);
      } catch (uptodownError) {
        console.log("❌ UPTODOWN FAIL:", uptodownError.message);
        throw new Error("All sources failed");
      }
    }

    console.log("📦 APK:", apkPath);

    // 5. Patch
    console.log("⬇️ PATCHING...");
    const patchedPath = patchApk(cli, patches, apkPath);

    console.log("📦 PATCHED (raw):", patchedPath);

    // 🔥 Morphe outputs patched APK in project root
    const dir = process.cwd();

    // 🔥 Get the newest patched APK (no version check)
    const patchedFile = fs.readdirSync(dir)
      .filter(f => f.endsWith("-patched.apk"))
      .map(f => ({
        name: f,
        time: fs.statSync(path.join(dir, f)).mtime.getTime()
      }))
      .sort((a, b) => b.time - a.time)[0]?.name;

    if (!patchedFile) {
      console.log("📂 FILES IN ROOT:");
      fs.readdirSync(dir).forEach(f => console.log(" -", f));
      throw new Error("Patched APK not found (*-patched.apk)");
    }

    const actualPatched = path.join(dir, patchedFile);

    console.log("🔍 FOUND PATCHED:", actualPatched);

    // 6. Rename to clean name
    const finalName = `youtube-${selectedVersion}-morphe.apk`;
    const finalPath = path.join(dir, finalName);

    fs.copyFileSync(actualPatched, finalPath);

    console.log("📝 FINAL:", finalPath);

    // (optional) cleanup original patched file
    // fs.unlinkSync(actualPatched);

    // 7. Upload to GitHub Release
    console.log("🚀 UPLOAD RELEASE...");
    await uploadApkRelease({
      version: selectedVersion,
      apkPath: finalPath,
    });

    // 8. Done
    console.log("\n🎉 DONE");
    console.log("──────────────");

    console.log("➡️ VERSION:", selectedVersion);
    console.log("📦 CLI:", cli);
    console.log("📦 PATCHES:", patches);
    console.log("📦 ORIGINAL:", apkPath);
    console.log("📦 OUTPUT:", finalPath);

  } catch (err) {
    console.error("\n❌ ERROR:", err.message);
    process.exit(1);
  }
})();
