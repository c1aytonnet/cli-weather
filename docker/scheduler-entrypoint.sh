#!/bin/sh
set -eu

SCHEDULE="${CLI_WEATHER_CRON_SCHEDULE:-0 7 * * *}"
TIMEZONE="${TZ:-UTC}"
CRON_FILE="/etc/cron.d/cli-weather"
CONFIG_DIR="${CLI_WEATHER_CONFIG_DIR:-}"
LOG_FILE="${CLI_WEATHER_LOG_PATH:-}"
ENV_FILE="/run/cli-weather/cli-weather.env"
RUNNER_SCRIPT="/usr/local/bin/cli-weather-cron-send"

if [ -z "$LOG_FILE" ]; then
  if [ -n "$CONFIG_DIR" ]; then
    LOG_FILE="${CONFIG_DIR}/scheduler.log"
  else
    LOG_FILE="/var/log/cli-weather.log"
  fi
fi

if [ -n "$CONFIG_DIR" ]; then
  mkdir -p "$CONFIG_DIR"
  mkdir -p "$CONFIG_DIR/secrets"
fi
touch "$LOG_FILE"
mkdir -p "$(dirname "$ENV_FILE")"

if [ -f "/usr/share/zoneinfo/${TIMEZONE}" ]; then
  ln -snf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
  echo "${TIMEZONE}" > /etc/timezone
else
  echo "Warning: timezone '${TIMEZONE}' was not found, falling back to UTC" >&2
  TIMEZONE="UTC"
  ln -snf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
  echo "${TIMEZONE}" > /etc/timezone
fi

quote_value() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g"
}

write_env_var() {
  VAR_NAME="$1"
  VAR_VALUE="$2"
  printf "%s='%s'\n" "$VAR_NAME" "$(quote_value "$VAR_VALUE")" >> "$ENV_FILE"
}

rm -f "$ENV_FILE"
write_env_var "CLI_WEATHER_LOCATION" "${CLI_WEATHER_LOCATION:-}"
write_env_var "CLI_WEATHER_RECIPIENT" "${CLI_WEATHER_RECIPIENT:-}"
write_env_var "CLI_WEATHER_SENDER" "${CLI_WEATHER_SENDER:-}"
write_env_var "CLI_WEATHER_SMTP_HOST" "${CLI_WEATHER_SMTP_HOST:-}"
write_env_var "CLI_WEATHER_SMTP_PORT" "${CLI_WEATHER_SMTP_PORT:-}"
write_env_var "CLI_WEATHER_SMTP_USERNAME" "${CLI_WEATHER_SMTP_USERNAME:-}"
write_env_var "CLI_WEATHER_SMTP_PASSWORD" "${CLI_WEATHER_SMTP_PASSWORD:-}"
write_env_var "CLI_WEATHER_SMTP_PASSWORD_FILE" "${CLI_WEATHER_SMTP_PASSWORD_FILE:-}"
write_env_var "CLI_WEATHER_SMTP_STARTTLS" "${CLI_WEATHER_SMTP_STARTTLS:-}"
write_env_var "CLI_WEATHER_SMTP_SSL" "${CLI_WEATHER_SMTP_SSL:-}"
write_env_var "CLI_WEATHER_PROVIDER" "${CLI_WEATHER_PROVIDER:-}"
write_env_var "CLI_WEATHER_VISUALCROSSING_API_KEY" "${CLI_WEATHER_VISUALCROSSING_API_KEY:-}"
write_env_var "CLI_WEATHER_VISUALCROSSING_API_KEY_FILE" "${CLI_WEATHER_VISUALCROSSING_API_KEY_FILE:-}"
write_env_var "CLI_WEATHER_CONFIG_DIR" "${CLI_WEATHER_CONFIG_DIR:-}"
write_env_var "CLI_WEATHER_CONFIG_PATH" "${CLI_WEATHER_CONFIG_PATH:-}"
write_env_var "CLI_WEATHER_LOG_PATH" "${LOG_FILE}"
write_env_var "TZ" "${TIMEZONE}"
chmod 0600 "$ENV_FILE"

cat > "$RUNNER_SCRIPT" <<EOF
#!/bin/sh
set -eu
. "$ENV_FILE"
exec cli-weather email send >> "$LOG_FILE" 2>&1
EOF
chmod 0700 "$RUNNER_SCRIPT"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=${TIMEZONE}
${SCHEDULE} root ${RUNNER_SCRIPT}
EOF

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"

echo "Installed cron schedule: ${SCHEDULE} (${TIMEZONE})"
echo "Tailing ${LOG_FILE}"

cron
exec tail -f "$LOG_FILE"
