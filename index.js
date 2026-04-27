const { execSync } = require("child_process");
const { downloadLatestGithubAsset } = require("./lib/github");
const { extractYoutubeVersions, pickLatestVersion } = require("./lib/versions");
const { downloadApk } = require("./lib/apkmirror");
const { downloadFromUptodown } = require("./lib/uptodown");
const { patchApk } = require("./lib/patcher");

(async () => {
  try {
    console.log("🚀 START\n");

    // 1. Tải CLI
    console.log("🌐 FETCH: morphe-cli (GitHub)");
    const cli = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-cli",
      match: (n) => n.includes("cli") && n.endsWith(".jar"),
    });
    console.log("📦 CLI:", cli);

    // 2. Tải patches
    console.log("🌐 FETCH: morphe-patches (GitHub)");
    const patches = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-patches",
      match: (n) => n.endsWith(".mpp"),
    });
    console.log("📦 PATCHES:", patches);

    // 3. Lấy version
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

    // 4. Download APK (có fallback)
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
    const patched = patchApk(cli, patches, apkPath);

    console.log("📦 PATCHED:", patched);

    // 6. Done
    console.log("\n🎉 DONE");
    console.log("──────────────");

    console.log("➡️ VERSION:", selectedVersion);
    console.log("📦 CLI:", cli);
    console.log("📦 PATCHES:", patches);
    console.log("📦 ORIGINAL:", apkPath);
    console.log("📦 OUTPUT:", patched);

  } catch (err) {
    console.error("\n❌ ERROR:", err.message);
    process.exit(1);
  }
})();
