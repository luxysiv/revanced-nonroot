function extractYoutubeVersions(output) {
  const results = [];
  const lines = output.split("\n");

  let inSection = false;

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("Most common compatible versions")) {
      inSection = true;
      continue;
    }

    if (inSection && !trimmed) break;

    if (inSection) {
      const match = trimmed.match(/^(\d+\.\d+\.\d+)\s+\((\d+)\s+patches\)/);

      if (match) {
        results.push({
          version: match[1],
          patches: Number(match[2]),
        });
      }
    }
  }

  if (!results.length) {
    const fallback = [...output.matchAll(/\d+\.\d+\.\d+/g)].map(m => m[0]);
    return fallback.map(v => ({ version: v, patches: 0 }));
  }

  return results;
}

function pickLatestVersion(list) {
  if (!list.length) return null;

  const sorted = list.sort((a, b) => {
    if (b.patches !== a.patches) {
      return b.patches - a.patches;
    }

    const pa = a.version.split(".").map(Number);
    const pb = b.version.split(".").map(Number);

    return (
      pb[0] - pa[0] ||
      pb[1] - pa[1] ||
      pb[2] - pa[2]
    );
  });

  return sorted[0].version;
}

function toApkMirrorVersion(version) {
  return version.replace(/\./g, "-");
}

module.exports = {
  extractYoutubeVersions,
  pickLatestVersion,
  toApkMirrorVersion,
};
