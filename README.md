# cli-weather

`cli-weather` is a command line weather app for macOS and Linux.

It can:
- print current conditions plus a 7-day forecast
- send the same report by email
- run scheduled email delivery, with Docker Compose as the preferred scheduler path

## Features

- Current weather and 7-day forecast in Fahrenheit
- U.S. ZIP code lookups
- U.S. city/state lookups such as `Austin, TX`
- International city/country lookups such as `Paris, France` and `London, GB`
- MET Norway as the default provider, with Open-Meteo and Visual Crossing as alternates
- Source attribution in the report output
- SMTP email delivery
- Docker Compose scheduler for preferred recurring jobs
- Native `crontab` scheduling as an alternative
- `.deb` and `.rpm` packaging assets for Linux distribution

## Installation

### From Source With Pip

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install .
```

### Debian Package

Build on a Linux machine with `dpkg-deb` available:

```bash
./scripts/build-deb.sh
```

Install:

```bash
sudo dpkg -i dist/cli-weather_0.5.0_all.deb
```

### RPM Package

Build on a Linux machine with `rpmbuild` available:

```bash
./scripts/build-rpm.sh
```

Install:

```bash
sudo rpm -i dist/rpmbuild/RPMS/noarch/cli-weather-0.5.0-1.noarch.rpm
```

## Basic Usage

```bash
cli-weather 78613
cli-weather "Austin, TX"
cli-weather "Paris, France"
cli-weather "London, GB"
```

The report includes:
- current conditions
- 7-day forecast
- rain probability and amount when available
- a source line at the bottom showing where the data came from

## Configuration

Config is stored at:

```bash
~/.config/cli-weather/config.json
```

Set a default location and provider:

```bash
cli-weather config set --location "Austin, TX"
cli-weather config set --provider metno
```

Set email configuration:

```bash
cli-weather config set --recipient you@example.com
cli-weather config set --sender you@example.com
cli-weather config set --smtp-host smtp.example.com --smtp-port 587
cli-weather config set --smtp-username you@example.com --smtp-password "app-password"
cli-weather config set --smtp-starttls true
```

Show the saved config:

```bash
cli-weather config show
```

## Provider Selection

Default:

```bash
cli-weather config set --provider metno
```

Other options:

```bash
cli-weather config set --provider open-meteo
cli-weather config set --provider visualcrossing --visualcrossing-api-key "your-api-key"
```

Provider notes:
- `metno` is the default and does not require an API key
- `open-meteo` does not require an API key
- `visualcrossing` requires an API key
- when `metno` is missing precipitation probability, the app automatically fills it from Open-Meteo

## Email Delivery

Send an email immediately:

```bash
cli-weather email send
cli-weather email send --location "Paris, France" --recipient friend@example.com
```

The email body intentionally matches the normal CLI text output.

## Scheduled Jobs

### Preferred: Docker Compose

Copy the sample environment file:

```bash
cp .env.example .env
```

Edit `.env` with your provider, location, SMTP settings, schedule, and timezone.

Useful example values:

```bash
CLI_WEATHER_PROVIDER=metno
CLI_WEATHER_LOCATION=Austin, TX
CLI_WEATHER_RECIPIENT=you@example.com
CLI_WEATHER_SENDER=you@example.com
CLI_WEATHER_SMTP_HOST=smtp.example.com
CLI_WEATHER_SMTP_PORT=587
CLI_WEATHER_SMTP_USERNAME=you@example.com
CLI_WEATHER_SMTP_PASSWORD=app-password
CLI_WEATHER_SMTP_STARTTLS=true
CLI_WEATHER_CRON_SCHEDULE=0 7 * * *
TZ=America/Chicago
```

Run an interactive weather check in Docker:

```bash
docker compose run --rm cli-weather cli-weather "Austin, TX"
```

Send a test email in Docker:

```bash
docker compose run --rm cli-weather cli-weather email send
```

Start the scheduler:

```bash
docker compose --profile scheduler up -d cli-weather-scheduler
```

Stop the scheduler:

```bash
docker compose --profile scheduler stop cli-weather-scheduler
```

Why Docker is recommended for scheduled jobs:
- keeps runtime and environment variables together
- avoids cron/path drift on the host
- makes scheduled behavior easier to move between machines

### Alternative: Host Cron

If you prefer a lighter native setup:

```bash
cli-weather schedule add --time 07:00
cli-weather schedule list
cli-weather schedule remove --time 07:00
```

This uses your user `crontab` and runs the installed `cli-weather email send` command automatically.

## Packaging Notes

The Linux packages install:
- the Python source into `/opt/cli-weather/src`
- a wrapper command at `/usr/bin/cli-weather`
- documentation in `/usr/share/doc/cli-weather`

The packages are intentionally simple and depend only on system `python3`.

## Troubleshooting

- If `cli-weather` is not found after a pip install, activate the virtual environment again with `source .venv/bin/activate`.
- If city/state lookups fail, use `City, ST` for U.S. searches and `City, Country` or `City, CountryCode` for international searches.
- If Visual Crossing is selected without a key, switch to `metno` or `open-meteo`, or configure `--visualcrossing-api-key`.
- If Docker scheduling is not sending mail, confirm the values in `.env`, especially SMTP settings, `CLI_WEATHER_LOCATION`, `CLI_WEATHER_CRON_SCHEDULE`, and `TZ`.

## License

MIT. See [LICENSE](LICENSE).
