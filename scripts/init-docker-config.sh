#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)

TARGET_ROOT="${1:-$(pwd)}"
APP_DIR="${TARGET_ROOT}/cli-weather"
SECRETS_DIR="${APP_DIR}/secrets"
ENV_EXAMPLE="${REPO_DIR}/.env.example"
ENV_FILE="${APP_DIR}/.env"
SMTP_SECRET_FILE="${SECRETS_DIR}/cli_weather_smtp_password.txt"
VC_SECRET_FILE="${SECRETS_DIR}/cli_weather_visualcrossing_api_key.txt"

mkdir -p "${SECRETS_DIR}"

if [ ! -f "${ENV_FILE}" ]; then
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  echo "Created ${ENV_FILE}"
else
  echo "Keeping existing ${ENV_FILE}"
fi

create_secret_file() {
  secret_file="$1"
  secret_label="$2"

  if [ ! -f "${secret_file}" ]; then
    : > "${secret_file}"
    echo "Created ${secret_file}"
  else
    echo "Keeping existing ${secret_file}"
  fi

  chmod 600 "${secret_file}"
  echo "Set permissions on ${secret_file} to 600 (${secret_label})"
}

create_secret_file "${SMTP_SECRET_FILE}" "SMTP password"
create_secret_file "${VC_SECRET_FILE}" "Visual Crossing API key"

cat <<EOF

Docker config bootstrap complete.

Files created or verified:
- ${ENV_FILE}
- ${SMTP_SECRET_FILE}
- ${VC_SECRET_FILE}

Next steps:
1. Edit ${ENV_FILE}
2. Put your SMTP app password into ${SMTP_SECRET_FILE}
3. If using Visual Crossing, put its API key into ${VC_SECRET_FILE}
4. Start services from ${TARGET_ROOT} with: docker compose up -d
EOF
