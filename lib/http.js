const https = require("https");

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

module.exports = { request };
