from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import CONFIG_PATH, load_config, set_config_values
from .emailer import EmailConfigurationError, send_weather_email, validate_email_config
from .scheduler import ScheduleError, add_schedule, list_schedules, remove_schedule
from .weather import WeatherLookupError, fetch_weather_report, format_weather_report


SUBCOMMANDS = {"config", "email", "schedule"}


def _build_config_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help=f"Path to config file (default: {CONFIG_PATH}).",
    )
    return parser


def build_root_parser() -> argparse.ArgumentParser:
    config_parent = _build_config_parent()
    parser = argparse.ArgumentParser(
        prog="cli-weather",
        description="Show weather reports and schedule email delivery.",
        epilog="Use `cli-weather 60601` or `cli-weather \"Chicago, IL\"` for direct lookups.",
        parents=[config_parent],
    )

    subparsers = parser.add_subparsers(dest="command")

    config_parser = subparsers.add_parser(
        "config",
        help="Show or update saved settings.",
        parents=[config_parent],
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    config_subparsers.add_parser("show", help="Print the saved configuration.", parents=[config_parent])

    config_set = config_subparsers.add_parser(
        "set",
        help="Update one or more config values.",
        parents=[config_parent],
    )
    config_set.add_argument("--provider", choices=["metno", "visualcrossing", "open-meteo"])
    config_set.add_argument("--location")
    config_set.add_argument("--recipient")
    config_set.add_argument("--sender")
    config_set.add_argument("--smtp-host")
    config_set.add_argument("--smtp-port", type=int)
    config_set.add_argument("--smtp-username")
    config_set.add_argument("--smtp-password")
    config_set.add_argument("--smtp-starttls", type=_parse_bool)
    config_set.add_argument("--smtp-ssl", type=_parse_bool)
    config_set.add_argument("--visualcrossing-api-key")

    email_parser = subparsers.add_parser(
        "email",
        help="Send a weather email now.",
        parents=[config_parent],
    )
    email_subparsers = email_parser.add_subparsers(dest="email_command", required=True)
    email_send = email_subparsers.add_parser(
        "send",
        help="Send weather email immediately.",
        parents=[config_parent],
    )
    email_send.add_argument("--location")
    email_send.add_argument("--recipient")

    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Manage cron schedules.",
        parents=[config_parent],
    )
    schedule_subparsers = schedule_parser.add_subparsers(dest="schedule_command", required=True)

    schedule_add = schedule_subparsers.add_parser(
        "add",
        help="Add a scheduled email job.",
        parents=[config_parent],
    )
    schedule_add.add_argument("--time", required=True, help="24-hour HH:MM time.")

    schedule_remove = schedule_subparsers.add_parser(
        "remove",
        help="Remove a scheduled email job.",
        parents=[config_parent],
    )
    schedule_remove.add_argument("--time", required=True, help="24-hour HH:MM time.")

    schedule_subparsers.add_parser(
        "list",
        help="List installed cli-weather cron jobs.",
        parents=[config_parent],
    )
    return parser


def build_weather_parser() -> argparse.ArgumentParser:
    config_parent = _build_config_parent()
    parser = argparse.ArgumentParser(
        prog="cli-weather",
        description="Show weather reports for a ZIP code or city/state.",
        parents=[config_parent],
    )
    parser.add_argument(
        "location",
        nargs="+",
        help="ZIP code or city/state in the form 'City, ST'.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config_override, argv = _extract_config_arg(argv)
    parser = build_root_parser()
    args = _parse_args(parser, argv)
    if config_override is not None:
        args.config = config_override

    try:
        if args.command == "config":
            return handle_config_command(args)
        if args.command == "email":
            return handle_email_command(args)
        if args.command == "schedule":
            return handle_schedule_command(args)
        return handle_weather_command(args)
    except (WeatherLookupError, EmailConfigurationError, ScheduleError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def handle_weather_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    location = args.location or config.get("location")
    if not location:
        raise ValueError("Provide a location or configure a default with `cli-weather config set --location ...`.")
    report = fetch_weather_report(
        location,
        provider=config.get("provider", "metno"),
        visualcrossing_api_key=config.get("visualcrossing_api_key", ""),
    )
    print(format_weather_report(report))
    return 0


def handle_config_command(args: argparse.Namespace) -> int:
    if args.config_command == "show":
        print(json.dumps(load_config(args.config), indent=2, sort_keys=True))
        return 0

    updates = {
        "provider": args.provider,
        "location": args.location,
        "recipient": args.recipient,
        "sender": args.sender,
        "smtp_host": args.smtp_host,
        "smtp_port": args.smtp_port,
        "smtp_username": args.smtp_username,
        "smtp_password": args.smtp_password,
        "smtp_starttls": args.smtp_starttls,
        "smtp_ssl": args.smtp_ssl,
        "visualcrossing_api_key": args.visualcrossing_api_key,
    }
    set_config_values(updates, args.config)
    print(f"Saved configuration to {args.config}")
    return 0


def handle_email_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    body = send_weather_email(config, location=args.location, recipient=args.recipient)
    print(body)
    return 0


def handle_schedule_command(args: argparse.Namespace) -> int:
    if args.schedule_command == "add":
        config = load_config(args.config)
        validate_email_config(config)
        if not config.get("location"):
            raise ValueError("Set a default location before installing a schedule.")
        cron_line = add_schedule(args.time, args.config)
        print(f"Installed schedule: {cron_line}")
        return 0
    if args.schedule_command == "remove":
        removed = remove_schedule(args.time)
        print(f"Removed {removed} schedule(s) for {args.time}")
        return 0
    schedules = list_schedules()
    if not schedules:
        print("No cli-weather schedules installed.")
        return 0
    for line in schedules:
        print(line)
    return 0


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("Boolean values must be true/false, yes/no, on/off, or 1/0.")


def _parse_args(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace:
    first_positional = _first_positional(argv)
    if first_positional and first_positional not in SUBCOMMANDS:
        weather_parser = build_weather_parser()
        weather_args = weather_parser.parse_args(argv)
        weather_args.location = " ".join(weather_args.location)
        weather_args.command = None
        return weather_args
    return parser.parse_args(argv)


def _first_positional(argv: list[str]) -> str | None:
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token == "--config":
            skip_next = True
            continue
        if token.startswith("--config="):
            continue
        if token.startswith("-"):
            continue
        return token
    return None


def _extract_config_arg(argv: list[str]) -> tuple[Path | None, list[str]]:
    config_path: Path | None = None
    remaining: list[str] = []
    skip_next = False

    for index, token in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if token == "--config":
            if index + 1 >= len(argv):
                raise ValueError("`--config` requires a path.")
            config_path = Path(argv[index + 1])
            skip_next = True
            continue
        if token.startswith("--config="):
            config_path = Path(token.split("=", 1)[1])
            continue
        remaining.append(token)

    return config_path, remaining


if __name__ == "__main__":
    raise SystemExit(main())
