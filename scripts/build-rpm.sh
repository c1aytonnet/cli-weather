#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
RPM_TOPDIR="${DIST_DIR}/rpmbuild"

command -v rpmbuild >/dev/null 2>&1 || {
  echo "rpmbuild is required to build the .rpm package." >&2
  exit 1
}

rm -rf "${RPM_TOPDIR}"
mkdir -p "${RPM_TOPDIR}/BUILD" "${RPM_TOPDIR}/BUILDROOT" "${RPM_TOPDIR}/RPMS" \
  "${RPM_TOPDIR}/SOURCES" "${RPM_TOPDIR}/SPECS" "${RPM_TOPDIR}/SRPMS"

cp "${ROOT_DIR}/packaging/rpm/cli-weather.spec" "${RPM_TOPDIR}/SPECS/cli-weather.spec"

rpmbuild -bb \
  --define "_topdir ${RPM_TOPDIR}" \
  --buildroot "${RPM_TOPDIR}/BUILDROOT" \
  "${RPM_TOPDIR}/SPECS/cli-weather.spec"

find "${RPM_TOPDIR}/RPMS" -name '*.rpm' -print
