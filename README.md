# cli-weather

`cli-weather` is a command line weather app for macOS and Linux.

It can:
- print current conditions plus a 7-day forecast
- send the same report by email
- run scheduled email delivery, with Docker Compose as the preferred scheduler path

## Recommended Installation

The preferred installation model is:

1. add `cli-weather` to your own existing Docker Compose stack
2. use the included `.deb` or `.rpm` package for native host installs only when you want a host-level command

If you already run other containers with Docker Compose, treat `cli-weather` as one more service in your own `compose.yaml`.

Recommended host layout for Docker:

```text
docker-media/
  compose.yaml
  cli-weather/
    .env
    config.json
    scheduler.log
    secrets/
      cli_weather_smtp_password.txt
      cli_weather_visualcrossing_api_key.txt
```

In this layout:
- `cli-weather/` is a normal host folder next to your `compose.yaml`
- the container bind-mounts that folder and persists its config and scheduler log there
- `config.json` is created if you use `cli-weather config set` or otherwise save config from inside the container
- `scheduler.log` is created when the scheduler container starts
- `.env` and any secret files are files you create on the host

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

### Option 1: Add To Your Own Docker Compose File

This is the recommended setup.

Recommended configuration model:
- put normal non-secret settings in `./cli-weather/.env`
- reference that file with `env_file: ./cli-weather/.env`
- keep secrets such as SMTP passwords and API keys out of `compose.yaml`
- prefer Docker secrets or mounted secret files with `*_FILE` variables for secrets

Use the published GitHub Container Registry image, then add these services to your own `compose.yaml`:

```yaml
services:
  cli-weather:
    image: ghcr.io/c1aytonnet/cli-weather:latest
    env_file:
      - ./cli-weather/.env
    environment:
      CLI_WEATHER_CONFIG_DIR: /data
      CLI_WEATHER_SMTP_PASSWORD_FILE: /run/secrets/cli_weather_smtp_password
    secrets:
      - cli_weather_smtp_password
    volumes:
      - ./cli-weather:/data
    command: ["cli-weather", "--help"]

  cli-weather-scheduler:
    image: ghcr.io/c1aytonnet/cli-weather:latest
    env_file:
      - ./cli-weather/.env
    environment:
      CLI_WEATHER_CONFIG_DIR: /data
      CLI_WEATHER_SMTP_PASSWORD_FILE: /run/secrets/cli_weather_smtp_password
    secrets:
      - cli_weather_smtp_password
    volumes:
      - ./cli-weather:/data
    entrypoint: ["/app/docker/scheduler-entrypoint.sh"]
    restart: unless-stopped

secrets:
  cli_weather_smtp_password:
    file: ./cli-weather/secrets/cli_weather_smtp_password.txt
```

If you use `visualcrossing` as the provider, add this to both services:

```yaml
environment:
  CLI_WEATHER_VISUALCROSSING_API_KEY_FILE: /run/secrets/cli_weather_visualcrossing_api_key
secrets:
  - cli_weather_visualcrossing_api_key
```

and add this secret definition:

```yaml
secrets:
  cli_weather_visualcrossing_api_key:
    file: ./cli-weather/secrets/cli_weather_visualcrossing_api_key.txt
```

Create the app folder and secret folder on the host:

```bash
./scripts/init-docker-config.sh .
```

That script:
- creates `./cli-weather/`
- copies `.env.example` to `./cli-weather/.env` if it does not already exist
- creates `./cli-weather/secrets/cli_weather_smtp_password.txt`
- creates `./cli-weather/secrets/cli_weather_visualcrossing_api_key.txt`
- sets the secret file permissions to `0600`
- leaves existing files in place if you already customized them

If you prefer to create the files manually, the equivalent commands are:

```bash
mkdir -p ./cli-weather/secrets
printf '%s\n' 'your-app-password' > ./cli-weather/secrets/cli_weather_smtp_password.txt
chmod 600 ./cli-weather/secrets/cli_weather_smtp_password.txt
```

If you use Visual Crossing:

```bash
printf '%s\n' 'your-visual-crossing-api-key' > ./cli-weather/secrets/cli_weather_visualcrossing_api_key.txt
chmod 600 ./cli-weather/secrets/cli_weather_visualcrossing_api_key.txt
```

Create `./cli-weather/.env` for the non-secret settings:

```env
CLI_WEATHER_PROVIDER=metno
CLI_WEATHER_LOCATION=Austin, TX
CLI_WEATHER_RECIPIENT=you@example.com,friend@example.com
CLI_WEATHER_SENDER=you@example.com
CLI_WEATHER_SMTP_HOST=smtp.example.com
CLI_WEATHER_SMTP_PORT=587
CLI_WEATHER_SMTP_USERNAME=you@example.com
CLI_WEATHER_SMTP_STARTTLS=true
CLI_WEATHER_SMTP_SSL=false
CLI_WEATHER_CRON_SCHEDULE=0 7 * * *
TZ=America/Chicago
```

In this model:
- `./cli-weather/.env` is the preferred place for ordinary configuration values
- the Compose `secrets:` section is the preferred place for SMTP passwords and API keys
- the bind-mounted `./cli-weather` folder is where the app stores `config.json` when you save config and `scheduler.log` when the scheduler runs
- you only put secrets directly in `environment:` when you intentionally accept that tradeoff

Then run:

```bash
docker compose pull cli-weather cli-weather-scheduler
docker compose run --rm cli-weather cli-weather "Austin, TX"
docker compose up -d cli-weather-scheduler
```

What those commands do:
- `docker compose pull cli-weather cli-weather-scheduler`
  Pulls the published image from GitHub Container Registry.
- `docker compose run --rm cli-weather cli-weather "Austin, TX"`
  Runs a one-off weather lookup inside a temporary container so you can verify the app works before enabling scheduled jobs.
- `docker compose up -d cli-weather-scheduler`
  Starts the background scheduler container, which uses cron to send email on the schedule defined by `CLI_WEATHER_CRON_SCHEDULE`.

This model is ideal when:
- you already manage services in your own Compose stack
- you want scheduled jobs to live alongside your other containers
- you prefer configuration to live in your own `./cli-weather/.env`, Compose secrets, and `compose.yaml`

### Option 2: Use The Included Docker Compose File

Use this if you want a quick standalone setup from this repo without merging into your existing stack.

Requirements:
- Docker
- Docker Compose
- access to `ghcr.io/c1aytonnet/cli-weather:latest`

Initial setup:

```bash
./scripts/init-docker-config.sh .
docker compose pull
```

After that, you can run one-off commands:

```bash
docker compose run --rm cli-weather cli-weather 78613
docker compose run --rm cli-weather cli-weather "Paris, France"
docker compose run --rm cli-weather cli-weather email send
```

### Option 3: Install Natively With Debian Or RPM Packages

### Debian Package

Prebuilt package artifact is tracked in git at:

```bash
release-assets/v0.5.0/cli-weather_0.5.0_all.deb
```

Install directly from the checked-out repository:

```bash
sudo dpkg -i release-assets/v0.5.0/cli-weather_0.5.0_all.deb
```

Or build a fresh package on Linux with `dpkg-deb` available:

```bash
./scripts/build-deb.sh
```

Install:

```bash
sudo dpkg -i dist/cli-weather_0.5.0_all.deb
```

### RPM Package

Prebuilt package artifact is tracked in git at:

```bash
release-assets/v0.5.0/cli-weather-0.5.0-1.noarch.rpm
```

Install directly from the checked-out repository:

```bash
sudo rpm -i release-assets/v0.5.0/cli-weather-0.5.0-1.noarch.rpm
```

Or build a fresh package on Linux with `rpmbuild` available:

```bash
./scripts/build-rpm.sh
```

Install:

```bash
sudo rpm -i dist/rpmbuild/RPMS/noarch/cli-weather-0.5.0-1.noarch.rpm
```

### Option 4: From Source With Pip

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install .
```

### Option 5: macOS CLI Install

If you want to use `cli-weather` as a normal persistent command on macOS, `pipx` is the recommended installation method.

Install `pipx`:

```bash
brew install pipx
pipx ensurepath
```

Then install `cli-weather` from the cloned repo:

```bash
git clone https://github.com/c1aytonnet/cli-weather.git
cd cli-weather
pipx install .
```

After that, you should be able to run:

```bash
cli-weather 78613
cli-weather "Austin, TX"
cli-weather "Paris, France"
```

If you prefer not to use `pipx`, you can still install from source with Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install .
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

In Docker, if you set `CLI_WEATHER_CONFIG_DIR=/data` and bind-mount `./cli-weather:/data`, the config file is stored at:

```bash
./cli-weather/config.json
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

Multiple recipients are supported by separating email addresses with commas:

```bash
cli-weather config set --recipient "you@example.com,friend@example.com"
```

Show the saved config:

```bash
cli-weather config show
```

Sensitive fields such as SMTP passwords and API keys are redacted in `config show`.

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

You can also send to multiple recipients:

```bash
cli-weather email send --recipient "you@example.com,friend@example.com"
```

The email body intentionally matches the normal CLI text output.

## Scheduled Jobs

### Preferred: Docker Compose

Copy the sample environment file:

```bash
./scripts/init-docker-config.sh .
```

Edit `./cli-weather/.env` with your provider, location, SMTP settings, schedule, and timezone.

For the included Compose setup, `./cli-weather/.env` is the preferred way to provide non-secret configuration. If you want stronger secret handling, replace plain password or API key values with `*_FILE` variables that point to mounted secret files.

Useful example values:

```bash
CLI_WEATHER_PROVIDER=metno
CLI_WEATHER_LOCATION=Austin, TX
CLI_WEATHER_RECIPIENT=you@example.com,friend@example.com
CLI_WEATHER_SENDER=you@example.com
CLI_WEATHER_SMTP_HOST=smtp.example.com
CLI_WEATHER_SMTP_PORT=587
CLI_WEATHER_SMTP_USERNAME=you@example.com
CLI_WEATHER_SMTP_PASSWORD=app-password
CLI_WEATHER_SMTP_STARTTLS=true
CLI_WEATHER_CRON_SCHEDULE=0 7 * * *
TZ=America/Chicago
```

If you are using secret files, remove plain secret values such as `CLI_WEATHER_SMTP_PASSWORD` and `CLI_WEATHER_VISUALCROSSING_API_KEY` from `./cli-weather/.env`.

Safer secret-file example:

```bash
CLI_WEATHER_SMTP_PASSWORD_FILE=/run/secrets/cli_weather_smtp_password
CLI_WEATHER_VISUALCROSSING_API_KEY_FILE=/run/secrets/cli_weather_visualcrossing_api_key
```

Supported Docker environment variables:

- `CLI_WEATHER_PROVIDER`
  Supported values: `metno`, `open-meteo`, `visualcrossing`
- `CLI_WEATHER_LOCATION`
  Examples: `78613`, `Austin, TX`, `Paris, France`
- `CLI_WEATHER_VISUALCROSSING_API_KEY`
  Required only when provider is `visualcrossing`
- `CLI_WEATHER_RECIPIENT`
  Destination email address for scheduled and immediate sends. Multiple addresses can be separated with commas.
- `CLI_WEATHER_SENDER`
  From address used in SMTP mail
- `CLI_WEATHER_SMTP_HOST`
  SMTP server hostname
- `CLI_WEATHER_SMTP_PORT`
  SMTP server port
- `CLI_WEATHER_SMTP_USERNAME`
  SMTP login username when required
- `CLI_WEATHER_SMTP_PASSWORD`
  SMTP login password when required. Prefer `CLI_WEATHER_SMTP_PASSWORD_FILE` for Docker deployments.
- `CLI_WEATHER_SMTP_PASSWORD_FILE`
  Optional path to a file containing the SMTP password. Prefer this over plain env vars when using Docker secrets.
- `CLI_WEATHER_SMTP_STARTTLS`
  `true` or `false`
- `CLI_WEATHER_SMTP_SSL`
  `true` or `false`
- `CLI_WEATHER_VISUALCROSSING_API_KEY_FILE`
  Optional path to a file containing the Visual Crossing API key. Prefer this over plain env vars in Docker when possible.
- `CLI_WEATHER_CRON_SCHEDULE`
  Standard cron expression used by the scheduler container, for example `0 7 * * *`
- `TZ`
  Timezone used by the scheduler container, for example `America/Chicago`

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

View scheduler logs:

```bash
docker compose --profile scheduler logs -f cli-weather-scheduler
```

Stop the scheduler:

```bash
docker compose --profile scheduler stop cli-weather-scheduler
```

Why Docker is recommended for scheduled jobs:
- keeps runtime and environment variables together
- avoids cron/path drift on the host
- makes scheduled behavior easier to move between machines
- fits naturally into existing multi-service Compose stacks
- gives the app a visible host folder such as `./cli-weather` for config and logs
- supports secret-file based configuration through `*_FILE` variables

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

## Security Notes

- Config files are written with owner-only permissions when possible.
- `cli-weather config show` redacts sensitive fields.
- For containerized deployments, prefer `CLI_WEATHER_SMTP_PASSWORD_FILE` and `CLI_WEATHER_VISUALCROSSING_API_KEY_FILE` over plain environment variables when you have Docker secrets or mounted secret files available.
- For Docker deployments, use a bind-mounted app folder such as `./cli-weather` so `config.json` and `scheduler.log` are easy to find on the host.
- Set host secret files such as `./cli-weather/secrets/cli_weather_smtp_password.txt` to `0600`.

## Container Image

The published container image is:

```bash
ghcr.io/c1aytonnet/cli-weather:latest
```

GitHub Actions publishes:
- `latest` from the default branch
- `v*` tag images from git release tags

## Troubleshooting

- If `cli-weather` is not found after a pip install, activate the virtual environment again with `source .venv/bin/activate`.
- If city/state lookups fail, use `City, ST` for U.S. searches and `City, Country` or `City, CountryCode` for international searches.
- If Visual Crossing is selected without a key, switch to `metno` or `open-meteo`, or configure `--visualcrossing-api-key`.
- If Docker scheduling is not sending mail, confirm the values in `./cli-weather/.env`, especially SMTP settings, `CLI_WEATHER_LOCATION`, `CLI_WEATHER_CRON_SCHEDULE`, and `TZ`.

## License

MIT. See [LICENSE](LICENSE).
