const { execSync } = require("child_process");

function patchApk(cli, patches, apk) {
  console.log("\n🛠️ Patching APK...\n");

  try {
    execSync(`
      java -jar "${cli}" patch \
        --patches "${patches}" \
        "${apk}"
    `, { stdio: "inherit" });

    const outputApk = apk.replace(".apk", ".patched.apk");

    console.log("\n✅ Patch done");
    return outputApk;

  } catch (err) {
    throw new Error("Patch failed");
  }
}

module.exports = { patchApk };
