const fs = require("fs");
const https = require("https");
const { execSync } = require("child_process");
const { chromium } = require("playwright");

// ================= HELPER =================
function request(url, headers = {}, retry = 3) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { headers }, res => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode)) {
        if (!res.headers.location) {
          return reject(new Error("Redirect không có location"));
        }
        return resolve(request(res.headers.location, headers, retry));
      }

      if (res.statusCode >= 400) {
        return reject(new Error(`HTTP ${res.statusCode}`));
      }

      resolve(res);
    });

    req.on("error", err => {
      if (retry > 0) {
        console.log(`🔁 Retry... (${retry})`);
        resolve(request(url, headers, retry - 1));
      } else {
        reject(err);
      }
    });
  });
}

// ================= DOWNLOAD GITHUB =================
async function downloadLatestGithubAsset({ owner, repo, match }) {
  const apiUrl = `https://api.github.com/repos/${owner}/${repo}/releases/latest`;

  console.log(`\n📦 Fetch release: ${owner}/${repo}`);

  const release = await fetch(apiUrl, {
    headers: { "User-Agent": "node" }
  }).then(r => r.json());

  if (!release.assets) {
    throw new Error(`Repo ${owner}/${repo} không có assets`);
  }

  const asset = release.assets.find(a => match(a.name));

  if (!asset) {
    throw new Error(`❌ Không tìm thấy asset trong ${repo}`);
  }

  console.log("🎯 Selected:", asset.name);

  if (fs.existsSync(asset.name)) {
    console.log("⚡ Skip (cached):", asset.name);
    return asset.name;
  }

  const file = fs.createWriteStream(asset.name);
  const res = await request(asset.browser_download_url, {
    "User-Agent": "node"
  });

  await new Promise((resolve, reject) => {
    res.pipe(file);
    file.on("finish", () => {
      file.close(resolve);
      console.log("✅ Done:", asset.name);
    });
    file.on("error", reject);
  });

  return asset.name;
}

// ================= PARSE VERSION =================
function extractYoutubeVersions(output) {
  const versions = new Set();
  const lines = output.split("\n");

  for (const line of lines) {
    const match = line.match(/\b\d+\.\d+\.\d+\b/);
    if (match) versions.add(match[0]);
  }

  return [...versions];
}

function toApkMirrorVersion(version) {
  return version.replace(/\./g, "-");
}

// ================= DOWNLOAD APK =================
async function downloadApk(version) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox']
  });

  const context = await browser.newContext({
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  });

  const page = await context.newPage();

  try {
    const versionSlug = toApkMirrorVersion(version);
    const baseUrl = `https://www.apkmirror.com/apk/google-inc/youtube/youtube-${versionSlug}-release/`;

    console.log("\n🌐 APK PAGE:", baseUrl);

    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });

    await page.waitForSelector('.table-row', { timeout: 60000 });

    const page2Link = await page.evaluate(() => {
      const rows = document.querySelectorAll('.table-row');

      for (const row of rows) {
        const cells = row.querySelectorAll('.table-cell');
        if (cells.length < 5) continue;

        const arch = cells[1].innerText.toLowerCase();
        const dpi = cells[3].innerText.toLowerCase();
        const isBundle = row.innerText.toLowerCase().includes('bundle');

        if (
          arch.includes('universal') &&
          dpi.includes('nodpi') &&
          !isBundle
        ) {
          return cells[0].querySelector('a.accent_color')?.href;
        }
      }
      return null;
    });

    if (!page2Link) throw new Error("Không có variant");

    console.log("➡️ Variant:", page2Link);

    await page.goto(page2Link, { waitUntil: 'domcontentloaded' });

    await page.waitForSelector('a.downloadButton');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('a.downloadButton')
    ]);

    const fileName = download.suggestedFilename();

    if (fs.existsSync(fileName)) {
      console.log("⚡ APK cached:", fileName);
      return fileName;
    }

    await download.saveAs(fileName);

    console.log("📦 APK:", fileName);

    return fileName;

  } finally {
    await browser.close();
  }
}

// ================= PATCH APK =================
function patchApk(cli, patches, apk) {
  console.log("\n🛠️ Patching APK...\n");

  const outputApk = apk.replace(".apk", ".patched.apk");

  try {
    execSync(`
      java -jar "${cli}" patch \
        --patches "${patches}" \
        "${apk}"
    `, { stdio: "inherit" });

    console.log("\n✅ Patch done");

    return outputApk;

  } catch (err) {
    throw new Error("Patch failed");
  }
}

// ================= MAIN =================
(async () => {
  try {
    console.log("🚀 START FULL FLOW\n");

    // 1. download tools
    const cli = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-cli",
      match: name => name.includes("cli") && name.endsWith(".jar")
    });

    const patches = await downloadLatestGithubAsset({
      owner: "MorpheApp",
      repo: "morphe-patches",
      match: name => name.endsWith(".mpp")
    });

    // 2. get version
    console.log("\n📋 Getting supported versions...\n");

    const output = execSync(`
      java -jar "${cli}" list-patches \
        --patches="${patches}" \
        --filter-package-name com.google.android.youtube \
        --with-versions
    `).toString();

    const versions = extractYoutubeVersions(output);

    if (!versions.length) {
      throw new Error("Không tìm được version nào");
    }

    const selectedVersion = versions.sort((a, b) =>
      b.localeCompare(a, undefined, { numeric: true })
    )[0];

    console.log("🎯 Selected version:", selectedVersion);

    // 3. download APK
    const apk = await downloadApk(selectedVersion);

    // 4. patch APK
    const patched = patchApk(cli, patches, apk);

    console.log("\n🎉 DONE");
    console.log({
      cli,
      patches,
      apk,
      patched,
      version: selectedVersion
    });

  } catch (err) {
    console.error("\n❌ ERROR:", err.message);
  }
})();
