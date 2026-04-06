#!/bin/sh
set -eu

CONFIG_DIR="${CLI_WEATHER_CONFIG_DIR:-}"
CONFIG_PATH="${CLI_WEATHER_CONFIG_PATH:-}"

if [ -n "$CONFIG_PATH" ]; then
  mkdir -p "$(dirname "$CONFIG_PATH")"
fi

if [ -n "$CONFIG_DIR" ]; then
  mkdir -p "$CONFIG_DIR"
  mkdir -p "$CONFIG_DIR/secrets"
fi

exec "$@"
