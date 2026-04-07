# Changelog

## 0.7.0 - 2026-04-07

- Added current weather and 7-day forecast CLI support for U.S. ZIP codes, U.S. city/state lookups, and international city/country lookups
- Added provider support for MET Norway, Open-Meteo, and Visual Crossing
- Made MET Norway the default provider
- Added automatic Open-Meteo precipitation fallback when MET Norway precipitation probability is unavailable
- Improved CLI output formatting with `Today` and `Tomorrow` labels, aligned forecast rows, precipitation details, and source attribution
- Added SMTP email delivery using the same text output as the CLI
- Added Docker Compose scheduling as the preferred recurring-job path
- Kept native host `crontab` scheduling as an alternative
- Added Debian and RPM packaging assets and build scripts
- Expanded repository documentation for installation, configuration, scheduling, provider selection, and package installation
