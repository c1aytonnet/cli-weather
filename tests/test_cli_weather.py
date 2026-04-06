from __future__ import annotations

import argparse
import json
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cli_weather import cli, config, emailer, scheduler, weather


class ConfigTests(unittest.TestCase):
    def test_config_path_honors_cli_weather_config_dir(self) -> None:
        import importlib
        import os

        original = os.environ.get("CLI_WEATHER_CONFIG_DIR")
        try:
            os.environ["CLI_WEATHER_CONFIG_DIR"] = "/tmp/cli-weather-data"
            reloaded = importlib.reload(config)
            self.assertEqual(reloaded.CONFIG_PATH, Path("/tmp/cli-weather-data/config.json"))
        finally:
            if original is None:
                os.environ.pop("CLI_WEATHER_CONFIG_DIR", None)
            else:
                os.environ["CLI_WEATHER_CONFIG_DIR"] = original
            importlib.reload(config)

    def test_set_config_values_persists_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config.set_config_values(
                {
                    "location": "Chicago, IL",
                    "recipient": "user@example.com",
                    "smtp_port": 2525,
                },
                config_path,
            )

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["location"], "Chicago, IL")
            self.assertEqual(saved["recipient"], "user@example.com")
            self.assertEqual(saved["smtp_port"], 2525)
            self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)

    @patch.dict(
        "os.environ",
        {
            "CLI_WEATHER_LOCATION": "78613",
            "CLI_WEATHER_SMTP_PORT": "465",
            "CLI_WEATHER_SMTP_SSL": "true",
        },
        clear=False,
    )
    def test_load_config_applies_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config.save_config({"location": "Chicago, IL", "smtp_port": 587, "smtp_ssl": False}, config_path)

            loaded = config.load_config(config_path)

            self.assertEqual(loaded["location"], "78613")
            self.assertEqual(loaded["smtp_port"], 465)
            self.assertTrue(loaded["smtp_ssl"])

    @patch.dict(
        "os.environ",
        {},
        clear=False,
    )
    def test_load_config_supports_file_based_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_path = Path(tmpdir) / "smtp_password.txt"
            secret_path.write_text("super-secret\n", encoding="utf-8")
            with patch.dict("os.environ", {"CLI_WEATHER_SMTP_PASSWORD_FILE": str(secret_path)}, clear=False):
                loaded = config.load_config(Path(tmpdir) / "missing.json")

            self.assertEqual(loaded["smtp_password"], "super-secret")

    def test_default_provider_is_metno(self) -> None:
        loaded = config.load_config(Path("/tmp/does-not-exist.json"))

        self.assertEqual(loaded["provider"], "metno")

    def test_redact_config_masks_secrets(self) -> None:
        redacted = config.redact_config(
            {
                "smtp_password": "secret",
                "visualcrossing_api_key": "api-key",
                "location": "Austin, TX",
            }
        )

        self.assertEqual(redacted["smtp_password"], "***redacted***")
        self.assertEqual(redacted["visualcrossing_api_key"], "***redacted***")
        self.assertEqual(redacted["location"], "Austin, TX")


class WeatherTests(unittest.TestCase):
    @patch("cli_weather.weather._get_json")
    def test_resolve_zip_code(self, get_json: MagicMock) -> None:
        get_json.return_value = {
            "places": [
                {
                    "place name": "Chicago",
                    "state abbreviation": "IL",
                    "latitude": "41.883",
                    "longitude": "-87.632",
                }
            ]
        }

        location = weather.resolve_location("60601")

        self.assertEqual(location.display_name, "Chicago, IL 60601")
        self.assertAlmostEqual(location.latitude, 41.883)
        self.assertAlmostEqual(location.longitude, -87.632)

    @patch("cli_weather.weather._get_json")
    def test_resolve_city_state_filters_by_state(self, get_json: MagicMock) -> None:
        get_json.return_value = {
            "results": [
                {
                    "name": "Austin",
                    "country_code": "US",
                    "admin1": "Minnesota",
                    "admin1_code": "US-MN",
                    "latitude": 43.6666,
                    "longitude": -92.9746,
                },
                {
                    "name": "Austin",
                    "country_code": "US",
                    "admin1": "Texas",
                    "admin1_code": "US-TX",
                    "latitude": 30.2711,
                    "longitude": -97.7437,
                },
            ]
        }

        location = weather.resolve_location("Austin, TX")

        self.assertEqual(location.display_name, "Austin, TX")
        self.assertAlmostEqual(location.latitude, 30.2711)
        self.assertAlmostEqual(location.longitude, -97.7437)

    @patch("cli_weather.weather._get_json")
    def test_resolve_international_place_by_country_code(self, get_json: MagicMock) -> None:
        get_json.return_value = {
            "results": [
                {
                    "name": "London",
                    "country": "Canada",
                    "country_code": "CA",
                    "latitude": 42.9834,
                    "longitude": -81.233,
                },
                {
                    "name": "London",
                    "country": "United Kingdom",
                    "country_code": "GB",
                    "latitude": 51.5085,
                    "longitude": -0.1257,
                },
            ]
        }

        location = weather.resolve_location("London, GB")

        self.assertEqual(location.display_name, "London, United Kingdom")
        self.assertAlmostEqual(location.latitude, 51.5085)
        self.assertAlmostEqual(location.longitude, -0.1257)

    @patch("cli_weather.weather._get_json")
    def test_resolve_international_place_by_country_name(self, get_json: MagicMock) -> None:
        get_json.return_value = {
            "results": [
                {
                    "name": "Paris",
                    "country": "United States",
                    "country_code": "US",
                    "latitude": 33.6609,
                    "longitude": -95.5555,
                },
                {
                    "name": "Paris",
                    "country": "France",
                    "country_code": "FR",
                    "latitude": 48.8534,
                    "longitude": 2.3488,
                },
            ]
        }

        location = weather.resolve_location("Paris, France")

        self.assertEqual(location.display_name, "Paris, France")
        self.assertAlmostEqual(location.latitude, 48.8534)
        self.assertAlmostEqual(location.longitude, 2.3488)

    @patch("cli_weather.weather._get_json")
    def test_fetch_metno_weather_report(self, get_json: MagicMock) -> None:
        get_json.side_effect = [
            {
                "places": [
                    {
                        "place name": "Chicago",
                        "state abbreviation": "IL",
                        "latitude": "41.883",
                        "longitude": "-87.632",
                    }
                ]
            },
            {
                "properties": {
                    "timeseries": [
                        {
                            "time": "2026-04-06T12:00:00Z",
                            "data": {
                                "instant": {
                                    "details": {
                                        "air_temperature": 15.5,
                                        "relative_humidity": 50,
                                        "wind_speed": 4.5,
                                    }
                                },
                                "next_1_hours": {
                                    "summary": {"symbol_code": "clearsky_day"},
                                    "details": {
                                        "precipitation_amount": 0.2,
                                    },
                                },
                            },
                        },
                        {
                            "time": "2026-04-07T12:00:00Z",
                            "data": {
                                "instant": {
                                    "details": {
                                        "air_temperature": 18.0,
                                        "relative_humidity": 55,
                                        "wind_speed": 5.0,
                                    }
                                },
                                "next_6_hours": {
                                    "summary": {"symbol_code": "lightrain"},
                                    "details": {
                                        "precipitation_amount": 3.0,
                                    },
                                },
                            },
                        },
                    ]
                }
            },
            {
                "current": {
                    "temperature_2m": 62.4,
                    "apparent_temperature": 60.1,
                    "relative_humidity_2m": 50,
                    "wind_speed_10m": 7.8,
                    "weather_code": 1,
                },
                "daily": {
                    "time": ["2026-04-06", "2026-04-07"],
                    "weather_code": [2, 63],
                    "temperature_2m_max": [68.1, 70.2],
                    "temperature_2m_min": [51.4, 55.0],
                    "precipitation_probability_max": [10, 40],
                },
            },
        ]

        report = weather.fetch_weather_report("60601", provider="metno")

        self.assertEqual(report["location"], "Chicago, IL 60601")
        self.assertEqual(report["current"]["summary"], "Clear sky")
        self.assertEqual(report["forecast"][0]["precipitation_probability"], 10)
        self.assertEqual(report["forecast"][1]["precipitation_probability"], 40)
        self.assertEqual(report["forecast"][0]["precipitation_amount_inches"], 0.01)
        self.assertEqual(report["sources"]["precipitation"], "MET Norway + Open-Meteo fallback")

    @patch("cli_weather.weather._get_json")
    def test_fetch_open_meteo_weather_report_formats_forecast(self, get_json: MagicMock) -> None:
        get_json.side_effect = [
            {
                "places": [
                    {
                        "place name": "Chicago",
                        "state abbreviation": "IL",
                        "latitude": "41.883",
                        "longitude": "-87.632",
                    }
                ]
            },
            {
                "current": {
                    "temperature_2m": 62.4,
                    "apparent_temperature": 60.1,
                    "relative_humidity_2m": 50,
                    "wind_speed_10m": 7.8,
                    "weather_code": 1,
                },
                "daily": {
                    "time": ["2026-04-06", "2026-04-07"],
                    "weather_code": [2, 63],
                    "temperature_2m_max": [68.1, 70.2],
                    "temperature_2m_min": [51.4, 55.0],
                    "precipitation_probability_max": [10, 70],
                },
            },
        ]

        report = weather.fetch_weather_report("60601", provider="open-meteo")
        rendered = weather.format_weather_report(report)

        self.assertEqual(report["location"], "Chicago, IL 60601")
        self.assertEqual(report["sources"]["forecast"], "Open-Meteo")
        self.assertIn("Current: 62F, Mostly clear (feels like 60F)", rendered)
        self.assertIn("Today (Mon Apr 6)", rendered)
        self.assertIn("Tomorrow (Tue Apr 7)", rendered)
        self.assertIn("Moderate rain", rendered)
        self.assertTrue(
            rendered.rstrip().endswith(
                "Sources: current Open-Meteo; forecast Open-Meteo; precipitation Open-Meteo"
            )
        )

    @patch("cli_weather.weather._get_json")
    def test_fetch_visualcrossing_weather_report(self, get_json: MagicMock) -> None:
        get_json.return_value = {
            "resolvedAddress": "Cedar Park, TX, United States",
            "currentConditions": {
                "temp": 60.4,
                "feelslike": 57.0,
                "humidity": 58,
                "windspeed": 9.7,
                "conditions": "Clear",
            },
            "days": [
                {
                    "datetime": "2026-04-06",
                    "conditions": "Overcast",
                    "tempmax": 69.2,
                    "tempmin": 47.1,
                    "precipprob": 0,
                },
                {
                    "datetime": "2026-04-07",
                    "conditions": "Rain",
                    "tempmax": 73.2,
                    "tempmin": 49.0,
                    "precipprob": 22,
                },
            ],
        }

        report = weather.fetch_weather_report(
            "78613",
            provider="visualcrossing",
            visualcrossing_api_key="test-key",
        )

        self.assertEqual(report["location"], "Cedar Park, TX, United States")
        self.assertEqual(report["current"]["temperature"], 60)
        self.assertEqual(report["forecast"][1]["summary"], "Rain")
        self.assertEqual(report["sources"]["current"], "Visual Crossing")

    def test_visualcrossing_requires_api_key(self) -> None:
        with self.assertRaises(weather.WeatherLookupError):
            weather.fetch_weather_report("78613", provider="visualcrossing")

    def test_city_state_requires_expected_format(self) -> None:
        with self.assertRaises(weather.WeatherLookupError) as excinfo:
            weather.resolve_location("Chicago Illinois")
        self.assertIn("Location must be provided as", str(excinfo.exception))


class EmailTests(unittest.TestCase):
    @patch("cli_weather.emailer.fetch_weather_report")
    @patch("cli_weather.emailer.smtplib.SMTP")
    def test_send_weather_email_uses_smtp_and_returns_body(
        self,
        smtp_cls: MagicMock,
        fetch_weather_report: MagicMock,
    ) -> None:
        fetch_weather_report.return_value = {
            "location": "Chicago, IL",
            "current": {
                "temperature": 62,
                "feels_like": 60,
                "humidity": 50,
                "wind_speed": 8,
                "summary": "Mostly clear",
            },
            "forecast": [
                {
                    "date": "2026-04-06",
                    "summary": "Partly cloudy",
                    "high": 68,
                    "low": 51,
                    "precipitation_probability": 10,
                }
            ],
        }
        smtp_instance = smtp_cls.return_value.__enter__.return_value
        smtp_instance.send_message = MagicMock()

        body = emailer.send_weather_email(
            {
                "provider": "metno",
                "location": "Chicago, IL",
                "recipient": "to@example.com",
                "sender": "from@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_username": "user",
                "smtp_password": "secret",
                "smtp_starttls": True,
                "smtp_ssl": False,
            }
        )

        self.assertIn("7-Day Forecast", body)
        fetch_weather_report.assert_called_once_with(
            "Chicago, IL",
            provider="metno",
            visualcrossing_api_key="",
        )
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("user", "secret")
        _, kwargs = smtp_instance.send_message.call_args
        self.assertEqual(kwargs["to_addrs"], ["to@example.com"])

    @patch("cli_weather.emailer.fetch_weather_report")
    @patch("cli_weather.emailer.smtplib.SMTP")
    def test_send_weather_email_splits_multiple_recipients(
        self,
        smtp_cls: MagicMock,
        fetch_weather_report: MagicMock,
    ) -> None:
        fetch_weather_report.return_value = {
            "location": "Chicago, IL",
            "current": {
                "temperature": 62,
                "feels_like": 60,
                "humidity": 50,
                "wind_speed": 8,
                "summary": "Mostly clear",
            },
            "forecast": [
                {
                    "date": "2026-04-06",
                    "summary": "Clear sky",
                    "high": 68,
                    "low": 51,
                    "precipitation_probability": 10,
                }
            ],
        }
        smtp_instance = smtp_cls.return_value.__enter__.return_value
        smtp_instance.send_message = MagicMock()

        emailer.send_weather_email(
            {
                "provider": "metno",
                "location": "Chicago, IL",
                "recipient": "to@example.com, friend@example.com",
                "sender": "from@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_starttls": True,
                "smtp_ssl": False,
            }
        )

        _, kwargs = smtp_instance.send_message.call_args
        self.assertEqual(kwargs["to_addrs"], ["to@example.com", "friend@example.com"])

    def test_validate_email_config_requires_core_fields(self) -> None:
        with self.assertRaises(emailer.EmailConfigurationError):
            emailer.validate_email_config({"recipient": "", "sender": "", "smtp_host": "", "smtp_port": 0})


class SchedulerTests(unittest.TestCase):
    @patch("cli_weather.scheduler.which", return_value="/usr/local/bin/cli-weather")
    def test_build_cli_command_quotes_config_path(self, which_mock: MagicMock) -> None:
        command = scheduler.build_cli_command(Path("/tmp/My Config/config.json"))

        self.assertIn("'/tmp/My Config/config.json'", command)
        self.assertIn("/usr/local/bin/cli-weather", command)
        which_mock.assert_called_once_with("cli-weather")

    @patch("cli_weather.scheduler._write_crontab")
    @patch("cli_weather.scheduler._get_crontab_lines", return_value=[])
    def test_add_schedule_appends_cron_entry(
        self,
        get_crontab_lines: MagicMock,
        write_crontab: MagicMock,
    ) -> None:
        cron_line = scheduler.add_schedule("07:30", Path("/tmp/config.json"), "cli-weather email send")

        self.assertIn("30 07 * * * cli-weather email send", cron_line)
        write_crontab.assert_called_once_with([cron_line])
        get_crontab_lines.assert_called_once()

    @patch("cli_weather.scheduler._write_crontab")
    @patch(
        "cli_weather.scheduler._get_crontab_lines",
        return_value=[
            "30 07 * * * cli-weather email send # cli-weather schedule 07:30",
            "@daily echo hi",
        ],
    )
    def test_remove_schedule_filters_matching_line(
        self,
        get_crontab_lines: MagicMock,
        write_crontab: MagicMock,
    ) -> None:
        removed = scheduler.remove_schedule("07:30")

        self.assertEqual(removed, 1)
        write_crontab.assert_called_once_with(["@daily echo hi"])
        get_crontab_lines.assert_called_once()


class CliTests(unittest.TestCase):
    def test_extract_config_arg_supports_equals_syntax(self) -> None:
        config_path, remaining = cli._extract_config_arg(["--config=/tmp/test.json", "config", "show"])

        self.assertEqual(config_path, Path("/tmp/test.json"))
        self.assertEqual(remaining, ["config", "show"])

    def test_parse_args_treats_plain_location_as_weather_lookup(self) -> None:
        args = cli._parse_args(cli.build_root_parser(), ["Chicago, IL"])

        self.assertIsNone(args.command)
        self.assertEqual(args.location, "Chicago, IL")

    @patch("cli_weather.cli.fetch_weather_report")
    @patch("cli_weather.cli.format_weather_report", return_value="REPORT")
    @patch("builtins.print")
    def test_handle_weather_command_uses_saved_location(
        self,
        print_mock: MagicMock,
        format_report: MagicMock,
        fetch_weather_report: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config.save_config({"location": "Chicago, IL"}, config_path)

            result = cli.handle_weather_command(SimpleNamespace(config=config_path, location=None))

            self.assertEqual(result, 0)
            fetch_weather_report.assert_called_once_with(
                "Chicago, IL",
                provider="metno",
                visualcrossing_api_key="",
            )
            format_report.assert_called_once()
            print_mock.assert_called_once_with("REPORT")

    @patch("cli_weather.cli.add_schedule", return_value="0 7 * * * cli-weather email send")
    @patch("builtins.print")
    def test_handle_schedule_add_requires_location_and_email_config(
        self,
        print_mock: MagicMock,
        add_schedule: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config.save_config(
                {
                    "location": "Chicago, IL",
                    "recipient": "to@example.com",
                    "sender": "from@example.com",
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                },
                config_path,
            )

            result = cli.handle_schedule_command(
                argparse.Namespace(schedule_command="add", time="07:00", config=config_path)
            )

            self.assertEqual(result, 0)
            add_schedule.assert_called_once_with("07:00", config_path)
            print_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
