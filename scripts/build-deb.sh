#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${DIST_DIR}/deb-build"
PACKAGE_ROOT="${BUILD_DIR}/cli-weather_0.6.0_all"

command -v dpkg-deb >/dev/null 2>&1 || {
  echo "dpkg-deb is required to build the .deb package." >&2
  exit 1
}

rm -rf "${BUILD_DIR}"
mkdir -p "${PACKAGE_ROOT}/DEBIAN"
mkdir -p "${PACKAGE_ROOT}/opt/cli-weather"
mkdir -p "${PACKAGE_ROOT}/usr/bin"
mkdir -p "${PACKAGE_ROOT}/usr/share/doc/cli-weather"

cp "${ROOT_DIR}/packaging/deb/control" "${PACKAGE_ROOT}/DEBIAN/control"
cp -R "${ROOT_DIR}/src" "${PACKAGE_ROOT}/opt/cli-weather/src"
cp "${ROOT_DIR}/README.md" "${PACKAGE_ROOT}/usr/share/doc/cli-weather/README.md"
cp "${ROOT_DIR}/LICENSE" "${PACKAGE_ROOT}/usr/share/doc/cli-weather/LICENSE"
install -m 0755 "${ROOT_DIR}/packaging/bin/cli-weather" "${PACKAGE_ROOT}/usr/bin/cli-weather"

mkdir -p "${DIST_DIR}"
dpkg-deb --build "${PACKAGE_ROOT}" "${DIST_DIR}/cli-weather_0.6.0_all.deb"
echo "Built ${DIST_DIR}/cli-weather_0.6.0_all.deb"
