const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const { downloadLatestGithubAsset } = require("./lib/github");
const {
  extractYoutubeVersions,
  pickLatestVersion,
} = require("./lib/versions");

const { downloadApk } = require("./lib/apkmirror");
const { downloadFromUptodown } = require("./lib/uptodown");
const { patchApk } = require("./lib/patcher");
const { uploadApkRelease } = require("./lib/release");

(async () => {
  try {
    console.log("🚀 START\n");

    // 1. Download CLI
    console.log("🌐 FETCH: morphe-cli");
    const cli = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-cli",
      match: (n) => n.includes("cli") && n.endsWith(".jar"),
    });
    console.log("📦 CLI:", cli);

    // 2. Download patches
    console.log("🌐 FETCH: morphe-patches");
    const patches = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-patches",
      match: (n) => n.endsWith(".mpp"),
    });
    console.log("📦 PATCHES:", patches);

    // 3. Extract versions
    console.log("⬇️ Extract versions (list-versions)...");

    const output = execSync(
      `java -jar "${cli}" list-versions \
        -f com.google.android.youtube \
        "${patches}"`,
      {
        encoding: "utf-8",
        maxBuffer: 1024 * 1024 * 10,
        stdio: "pipe",
      }
    );

    const versions = extractYoutubeVersions(output);

    if (!versions.length) {
      throw new Error("No versions found from CLI");
    }

    console.log("📋 ALL VERSIONS:");
    versions.forEach((v) => console.log(" -", v));

    const selectedVersion = pickLatestVersion(versions);

    if (!selectedVersion) {
      throw new Error("Failed to pick latest version");
    }

    console.log("\n➡️ TARGET:", selectedVersion);

    // 4. Download APK
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

    const dir = process.cwd();

    const patchedFile = fs
      .readdirSync(dir)
      .filter((f) => f.endsWith("-patched.apk"))
      .map((f) => ({
        name: f,
        time: fs.statSync(path.join(dir, f)).mtime.getTime(),
      }))
      .sort((a, b) => b.time - a.time)[0]?.name;

    if (!patchedFile) {
      console.log("📂 FILES IN ROOT:");
      fs.readdirSync(dir).forEach((f) => console.log(" -", f));
      throw new Error("Patched APK not found (*-patched.apk)");
    }

    const actualPatched = path.join(dir, patchedFile);

    console.log("🔍 FOUND PATCHED:", actualPatched);

    // 6. Rename
    const finalName = `youtube-${selectedVersion}-morphe.apk`;
    const finalPath = path.join(dir, finalName);

    fs.copyFileSync(actualPatched, finalPath);

    console.log("📝 FINAL:", finalPath);

    // 7. Upload
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

    if (err.stdout || err.stderr) {
      console.error("STDOUT:", err.stdout?.toString());
      console.error("STDERR:", err.stderr?.toString());
    }

    process.exit(1);
  }
})();
