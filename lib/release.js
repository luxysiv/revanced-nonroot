const fs = require("fs");
const path = require("path");
const https = require("https");

const TOKEN = process.env.GITHUB_TOKEN;
const REPO = process.env.GITHUB_REPOSITORY;

function request(options, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (d) => (data += d));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

const baseHeaders = {
  "User-Agent": "node",
  Authorization: `Bearer ${TOKEN}`,
  Accept: "application/vnd.github+json",
};

// 🔹 Get or create release
async function getOrCreateRelease(tag) {
  let res = await request({
    hostname: "api.github.com",
    path: `/repos/${REPO}/releases/tags/${tag}`,
    method: "GET",
    headers: baseHeaders,
  });

  if (res.message === "Not Found") {
    console.log("🆕 Creating release:", tag);

    res = await request(
      {
        hostname: "api.github.com",
        path: `/repos/${REPO}/releases`,
        method: "POST",
        headers: baseHeaders,
      },
      JSON.stringify({
        tag_name: tag,
        name: tag,
        draft: false,
        prerelease: false,
      })
    );
  }

  return res;
}

// 🔥 Get assets of a release
async function getReleaseAssets(releaseId) {
  return request({
    hostname: "api.github.com",
    path: `/repos/${REPO}/releases/${releaseId}/assets`,
    method: "GET",
    headers: baseHeaders,
  });
}

// 🔥 Delete asset by ID
async function deleteAsset(assetId) {
  return request({
    hostname: "api.github.com",
    path: `/repos/${REPO}/releases/assets/${assetId}`,
    method: "DELETE",
    headers: baseHeaders,
  });
}

// 🔥 Upload asset
async function uploadAsset(uploadUrl, filePath) {
  const fileName = path.basename(filePath);
  const fileData = fs.readFileSync(filePath);

  const url = new URL(
    uploadUrl.replace("{?name,label}", `?name=${encodeURIComponent(fileName)}`)
  );

  return request(
    {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: "POST",
      headers: {
        "User-Agent": "node",
        Authorization: `Bearer ${TOKEN}`,
        "Content-Type": "application/vnd.android.package-archive",
        "Content-Length": fileData.length,
      },
    },
    fileData
  );
}

// 🚀 Main upload with replace logic
async function uploadApkRelease({ version, apkPath }) {
  if (!TOKEN) throw new Error("Missing GITHUB_TOKEN");
  if (!REPO) throw new Error("Missing GITHUB_REPOSITORY");

  const tag = `youtube-${version}`;
  const fileName = path.basename(apkPath);

  const release = await getOrCreateRelease(tag);

  // 🔥 Check existing assets
  const assets = await getReleaseAssets(release.id);

  const existing = assets.find(a => a.name === fileName);

  if (existing) {
    console.log("♻️ Deleting existing asset:", fileName);
    await deleteAsset(existing.id);
  }

  console.log("📤 Uploading:", fileName);

  const res = await uploadAsset(release.upload_url, apkPath);

  console.log("✅ Uploaded:", res.browser_download_url);

  return res;
}

module.exports = { uploadApkRelease };
