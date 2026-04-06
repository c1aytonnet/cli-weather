#!/bin/sh
set -eu

SCHEDULE="${CLI_WEATHER_CRON_SCHEDULE:-0 7 * * *}"
TIMEZONE="${TZ:-UTC}"
CRON_FILE="/etc/cron.d/cli-weather"
LOG_FILE="/var/log/cli-weather.log"

touch "$LOG_FILE"

if [ -f "/usr/share/zoneinfo/${TIMEZONE}" ]; then
  ln -snf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
  echo "${TIMEZONE}" > /etc/timezone
else
  echo "Warning: timezone '${TIMEZONE}' was not found, falling back to UTC" >&2
  TIMEZONE="UTC"
  ln -snf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
  echo "${TIMEZONE}" > /etc/timezone
fi

cat > "$CRON_FILE" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=${TIMEZONE}
CLI_WEATHER_LOCATION=${CLI_WEATHER_LOCATION:-}
CLI_WEATHER_RECIPIENT=${CLI_WEATHER_RECIPIENT:-}
CLI_WEATHER_SENDER=${CLI_WEATHER_SENDER:-}
CLI_WEATHER_SMTP_HOST=${CLI_WEATHER_SMTP_HOST:-}
CLI_WEATHER_SMTP_PORT=${CLI_WEATHER_SMTP_PORT:-}
CLI_WEATHER_SMTP_USERNAME=${CLI_WEATHER_SMTP_USERNAME:-}
CLI_WEATHER_SMTP_PASSWORD=${CLI_WEATHER_SMTP_PASSWORD:-}
CLI_WEATHER_SMTP_STARTTLS=${CLI_WEATHER_SMTP_STARTTLS:-}
CLI_WEATHER_SMTP_SSL=${CLI_WEATHER_SMTP_SSL:-}
${SCHEDULE} root cli-weather email send >> ${LOG_FILE} 2>&1
EOF

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"

echo "Installed cron schedule: ${SCHEDULE} (${TIMEZONE})"
echo "Tailing ${LOG_FILE}"

cron
exec tail -f "$LOG_FILE"
