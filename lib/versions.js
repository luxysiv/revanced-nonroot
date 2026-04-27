function extractYoutubeVersions(output) {
  const versions = new Set();

  for (const line of output.split("\n")) {
    const match = line.match(/\b\d+\.\d+\.\d+\b/);
    if (match) versions.add(match[0]);
  }

  return [...versions];
}

function pickLatestVersion(list) {
  return list.sort((a, b) =>
    b.localeCompare(a, undefined, { numeric: true })
  )[0];
}

function toApkMirrorVersion(version) {
  return version.replace(/\./g, "-");
}

module.exports = {
  extractYoutubeVersions,
  pickLatestVersion,
  toApkMirrorVersion
};
