from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import List


CRON_MARKER = "# cli-weather schedule"
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ScheduleError(RuntimeError):
    pass


def validate_time(time_text: str) -> str:
    match = TIME_RE.fullmatch(time_text)
    if not match:
        raise ScheduleError("Time must be in 24-hour HH:MM format.")
    return time_text


def add_schedule(time_text: str, config_path: Path, cli_command: str | None = None) -> str:
    validate_time(time_text)
    hour, minute = time_text.split(":")
    command = cli_command or build_cli_command(config_path)
    cron_line = f"{minute} {hour} * * * {command} {CRON_MARKER} {time_text}"
    lines = _get_crontab_lines()
    if any(line.endswith(f"{CRON_MARKER} {time_text}") for line in lines):
        raise ScheduleError(f"A cli-weather schedule for {time_text} already exists.")
    lines.append(cron_line)
    _write_crontab(lines)
    return cron_line


def remove_schedule(time_text: str) -> int:
    validate_time(time_text)
    lines = _get_crontab_lines()
    filtered = [line for line in lines if not line.endswith(f"{CRON_MARKER} {time_text}")]
    removed = len(lines) - len(filtered)
    if removed == 0:
        raise ScheduleError(f"No cli-weather schedule found for {time_text}.")
    _write_crontab(filtered)
    return removed


def list_schedules() -> List[str]:
    return [line for line in _get_crontab_lines() if CRON_MARKER in line]


def build_cli_command(config_path: Path) -> str:
    installed_binary = which("cli-weather")
    if installed_binary:
        return (
            f"{shlex.quote(installed_binary)} email send --config "
            f"{shlex.quote(str(config_path))}"
        )
    return (
        f"{shlex.quote(sys.executable)} -m cli_weather.cli email send --config "
        f"{shlex.quote(str(config_path))}"
    )


def _get_crontab_lines() -> List[str]:
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, PermissionError) as exc:
        raise ScheduleError("`crontab` is not installed or not available in PATH.") from exc
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "no crontab" in stderr:
            return []
        raise ScheduleError(result.stderr.strip() or "Unable to read crontab.")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _write_crontab(lines: List[str]) -> None:
    content = "\n".join(lines) + ("\n" if lines else "")
    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=content,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, PermissionError) as exc:
        raise ScheduleError("`crontab` is not installed or not available in PATH.") from exc
    if result.returncode != 0:
        raise ScheduleError(result.stderr.strip() or "Unable to update crontab.")
