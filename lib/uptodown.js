const https = require("https");
const fs = require("fs");
const path = require("path");

const BASE = "https://youtube.en.uptodown.com/android";

// Helper fetch nội bộ
function fetch(url, headers = {}, isBinary = false) {
  return new Promise((resolve, reject) => {
    https.get(
      url,
      {
        headers: {
          "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
          ...headers,
        },
      },
      (res) => {
        let data = [];
        res.on("data", (c) => data.push(c));
        res.on("end", () => {
          const buffer = Buffer.concat(data);
          resolve({
            status: res.statusCode,
            headers: res.headers,
            body: isBinary ? buffer : buffer.toString(),
          });
        });
      }
    ).on("error", reject);
  });
}

async function downloadFromUptodown(version) {
  try {
    console.log("🌐 BASE:", BASE);
    console.log("🔎 VERSION:", version);

    // 1. Lấy appCode
    console.log("⬇️ Fetch versions page...");
    const html = (await fetch(`${BASE}/versions`)).body;

    const codeMatch = html.match(
      /id="detail-app-name"[^>]*data-code="(\d+)"/
    );
    if (!codeMatch) throw new Error("No appCode found");

    const appCode = codeMatch[1];
    console.log("🧩 APP CODE:", appCode);

    // 2. Tìm versionId
    let page = 1;
    let versionId = null;

    while (page < 10) {
      const apiUrl = `${BASE}/apps/${appCode}/versions/${page}`;
      console.log("🌐 PAGE:", apiUrl);

      const res = await fetch(apiUrl);
      const json = JSON.parse(res.body);

      if (!json.data || json.data.length === 0) break;

      const target = json.data.find(
        (item) =>
          item.version === version && item.kindFile === "apk"
      );

      if (target) {
        versionId = target.versionURL.versionID;
        break;
      }

      page++;
    }

    if (!versionId) throw new Error("No version found");

    console.log("➡️ VERSION ID:", versionId);

    // 3. Lấy token
    const pageUrl = `${BASE}/download/${versionId}`;
    console.log("🌐 DOWNLOAD PAGE:", pageUrl);

    const pageRes = await fetch(pageUrl, {
      referer: `${BASE}/versions`,
    });

    const tokenMatch = pageRes.body.match(
      /id="detail-download-button"[^>]*data-url="([^"]+)"/
    );

    if (!tokenMatch) throw new Error("No download token");

    const token = tokenMatch[1];
    const finalUrl = `https://dw.uptodown.com/dwn/${token}`;

    console.log("🔗 FINAL:", finalUrl);

    // 4. Tải file
    const outDir = path.resolve(__dirname, "..", "downloads");
    if (!fs.existsSync(outDir))
      fs.mkdirSync(outDir, { recursive: true });

    const filePath = path.join(
      outDir,
      `youtube-${version.replace(/\./g, "-")}-uptodown.apk`
    );

    console.log("⬇️ Downloading via HTTP...");

    let res = await fetch(finalUrl, { referer: pageUrl }, true);

    // redirect nếu có
    if (
      res.status >= 300 &&
      res.status < 400 &&
      res.headers.location
    ) {
      console.log("🔁 Redirect:", res.headers.location);
      res = await fetch(res.headers.location, {}, true);
    }

    if (res.status === 200) {
      fs.writeFileSync(filePath, res.body);
      console.log("📦 DONE:", filePath);
      return filePath;
    }

    throw new Error("Download failed: " + res.status);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    throw err;
  }
}

module.exports = { downloadFromUptodown };
