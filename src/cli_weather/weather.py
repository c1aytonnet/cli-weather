from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ZIP_CODE_RE = re.compile(r"^\d{5}$")
STATE_CODE_RE = re.compile(r"^[A-Za-z]{2}$")
HTTP_TIMEOUT_SECONDS = 15
METNO_USER_AGENT = "cli-weather/0.1.0 (https://example.com/contact)"

STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

METNO_SYMBOLS = {
    "clearsky": "Clear sky",
    "fair": "Fair",
    "partlycloudy": "Partly cloudy",
    "cloudy": "Cloudy",
    "fog": "Fog",
    "lightrain": "Light rain",
    "rain": "Rain",
    "heavyrain": "Heavy rain",
    "rainshowers": "Rain showers",
    "lightrainshowers": "Light rain showers",
    "heavyrainshowers": "Heavy rain showers",
    "lightsnow": "Light snow",
    "snow": "Snow",
    "heavysnow": "Heavy snow",
    "sleet": "Sleet",
    "thunderstorm": "Thunderstorm",
}


class WeatherLookupError(RuntimeError):
    pass


@dataclass
class Location:
    display_name: str
    latitude: float
    longitude: float


def _get_json(url: str, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    try:
        request = Request(url, headers=headers or {})
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as exc:
        raise WeatherLookupError(f"Weather service returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise WeatherLookupError(f"Unable to reach weather service: {exc.reason}") from exc


def resolve_location(query: str) -> Location:
    query = query.strip()
    if not query:
        raise WeatherLookupError("Location cannot be empty.")
    if ZIP_CODE_RE.fullmatch(query):
        return _resolve_zip_code(query)
    return _resolve_place(query)


def _resolve_zip_code(zip_code: str) -> Location:
    payload = _get_json(f"https://api.zippopotam.us/us/{zip_code}")
    places = payload.get("places") or []
    if not places:
        raise WeatherLookupError(f"No location found for ZIP code {zip_code}.")
    place = places[0]
    city = place.get("place name", "").strip()
    state = place.get("state abbreviation", "").strip()
    return Location(
        display_name=f"{city}, {state} {zip_code}",
        latitude=float(place["latitude"]),
        longitude=float(place["longitude"]),
    )


def _resolve_place(query: str) -> Location:
    primary, secondary = _parse_place_query(query)
    if secondary.upper() in STATE_NAMES:
        return _resolve_us_city_state(primary, secondary.upper(), query)
    return _resolve_international_place(primary, secondary, query)


def _resolve_us_city_state(city: str, state_code: str, original_query: str) -> Location:
    encoded_query = quote(city)
    payload = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_query}&count=20&language=en&format=json&countryCode=US"
    )
    results = payload.get("results") or []
    if not results:
        raise WeatherLookupError(f"No location found for '{original_query}'.")

    state_name = STATE_NAMES[state_code]
    for result in results:
        if _result_matches_state(result, state_code, state_name):
            name = result.get("name", city)
            return Location(
                display_name=f"{name}, {state_code}",
                latitude=float(result["latitude"]),
                longitude=float(result["longitude"]),
            )

    first_us = next((item for item in results if item.get("country_code") == "US"), None)
    if not first_us:
        raise WeatherLookupError(f"No U.S. match found for '{original_query}'.")
    return Location(
        display_name=f"{first_us.get('name', city)}, {state_code}",
        latitude=float(first_us["latitude"]),
        longitude=float(first_us["longitude"]),
    )


def _resolve_international_place(primary: str, secondary: str, original_query: str) -> Location:
    encoded_query = quote(primary)
    payload = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_query}&count=20&language=en&format=json"
    )
    results = payload.get("results") or []
    if not results:
        raise WeatherLookupError(f"No location found for '{original_query}'.")

    normalized_secondary = secondary.strip().lower()
    for result in results:
        if _result_matches_country(result, normalized_secondary):
            name = result.get("name", primary)
            country_name = (result.get("country") or "").strip()
            country_code = (result.get("country_code") or "").strip()
            display_suffix = country_name or country_code or secondary
            return Location(
                display_name=f"{name}, {display_suffix}",
                latitude=float(result["latitude"]),
                longitude=float(result["longitude"]),
            )

    raise WeatherLookupError(f"No location found for '{original_query}'.")


def _parse_place_query(query: str) -> List[str]:
    parts = [part.strip() for part in query.split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise WeatherLookupError(
            "Location must be provided as 'City, ST' for U.S. searches or 'City, Country' for international searches."
        )
    return [parts[0], parts[1]]


def fetch_weather_report(
    query: str,
    provider: str = "metno",
    visualcrossing_api_key: str = "",
) -> Dict[str, Any]:
    normalized_provider = provider.strip().lower()
    if normalized_provider == "metno":
        return _fetch_metno_weather_report(query)
    if normalized_provider == "visualcrossing":
        return _fetch_visualcrossing_weather_report(query, visualcrossing_api_key)
    if normalized_provider == "open-meteo":
        return _fetch_open_meteo_weather_report(query)
    raise WeatherLookupError(
        f"Unsupported weather provider '{provider}'. Use 'metno', 'visualcrossing', or 'open-meteo'."
    )


def _fetch_open_meteo_weather_report(query: str) -> Dict[str, Any]:
    location = resolve_location(query)
    return _fetch_open_meteo_weather_report_for_location(location)


def _fetch_open_meteo_weather_report_for_location(location: Location) -> Dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={location.latitude}&longitude={location.longitude}"
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&temperature_unit=fahrenheit"
        "&wind_speed_unit=mph"
        "&precipitation_unit=inch"
        "&forecast_days=7"
        "&timezone=auto"
    )
    payload = _get_json(url)
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    if not current or not daily:
        raise WeatherLookupError("Weather service did not return a complete forecast.")

    forecast = []
    for index, date in enumerate(daily.get("time", [])):
        forecast.append(
            {
                "date": date,
                "summary": describe_weather_code(daily["weather_code"][index]),
                "high": round(daily["temperature_2m_max"][index]),
                "low": round(daily["temperature_2m_min"][index]),
                "precipitation_probability": daily["precipitation_probability_max"][index],
            }
        )

    return {
        "location": location.display_name,
        "current": {
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": current["relative_humidity_2m"],
            "wind_speed": round(current["wind_speed_10m"]),
            "summary": describe_weather_code(current["weather_code"]),
        },
        "forecast": forecast,
        "sources": {
            "current": "Open-Meteo",
            "forecast": "Open-Meteo",
            "precipitation": "Open-Meteo",
        },
    }


def _fetch_metno_weather_report(query: str) -> Dict[str, Any]:
    location = resolve_location(query)
    payload = _get_json(
        "https://api.met.no/weatherapi/locationforecast/2.0/complete"
        f"?lat={location.latitude}&lon={location.longitude}",
        headers={"User-Agent": METNO_USER_AGENT},
    )
    timeseries = payload.get("properties", {}).get("timeseries") or []
    if not timeseries:
        raise WeatherLookupError("MET Norway did not return a complete forecast.")

    current_entry = timeseries[0]
    current_details = current_entry.get("data", {}).get("instant", {}).get("details", {})
    if not current_details:
        raise WeatherLookupError("MET Norway did not return current conditions.")

    daily_buckets: Dict[str, Dict[str, Any]] = {}
    for entry in timeseries:
        timestamp = entry.get("time")
        if not timestamp:
            continue
        entry_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        day_key = entry_time.date().isoformat()
        bucket = daily_buckets.setdefault(
            day_key,
            {
                "date": day_key,
                "high": None,
                "low": None,
                "summary": None,
                "precipitation_probability": None,
                "precipitation_amount_inches": 0.0,
            },
        )

        details = entry.get("data", {}).get("instant", {}).get("details", {})
        temperature = details.get("air_temperature")
        if temperature is not None:
            rounded_temp = round(_celsius_to_fahrenheit(temperature))
            bucket["high"] = rounded_temp if bucket["high"] is None else max(bucket["high"], rounded_temp)
            bucket["low"] = rounded_temp if bucket["low"] is None else min(bucket["low"], rounded_temp)

        period = _extract_metno_period(entry.get("data", {}))
        summary = period.get("summary")
        if summary and (
            bucket["summary"] is None or 6 <= entry_time.hour <= 18
        ):
            bucket["summary"] = summary
        probability = period.get("precipitation_probability")
        if probability is not None:
            rounded_probability = round(probability)
            current_probability = bucket["precipitation_probability"]
            if current_probability is None or rounded_probability > current_probability:
                bucket["precipitation_probability"] = rounded_probability
        amount_mm = period.get("precipitation_amount")
        if amount_mm is not None:
            bucket["precipitation_amount_inches"] += _millimeters_to_inches(amount_mm)

    forecast = []
    for day_key in sorted(daily_buckets.keys())[:7]:
        bucket = daily_buckets[day_key]
        forecast.append(
            {
                "date": bucket["date"],
                "summary": bucket["summary"] or "Unknown",
                "high": bucket["high"] if bucket["high"] is not None else 0,
                "low": bucket["low"] if bucket["low"] is not None else 0,
                "precipitation_probability": bucket["precipitation_probability"],
                "precipitation_amount_inches": round(bucket["precipitation_amount_inches"], 2),
            }
        )

    precipitation_source = "MET Norway"
    if any(day["precipitation_probability"] is None for day in forecast):
        forecast, used_open_meteo_fallback = _enrich_forecast_with_open_meteo_precipitation(location, forecast)
        if used_open_meteo_fallback:
            precipitation_source = "MET Norway + Open-Meteo fallback"

    current_summary = _extract_metno_period(current_entry.get("data", {})).get("summary") or "Unknown"
    return {
        "location": location.display_name,
        "current": {
            "temperature": round(_celsius_to_fahrenheit(current_details["air_temperature"])),
            "feels_like": round(
                _celsius_to_fahrenheit(current_details.get("air_temperature", 0))
            ),
            "humidity": round(current_details.get("relative_humidity", 0)),
            "wind_speed": round(_meters_per_second_to_mph(current_details.get("wind_speed", 0))),
            "summary": current_summary,
        },
        "forecast": forecast,
        "sources": {
            "current": "MET Norway",
            "forecast": "MET Norway",
            "precipitation": precipitation_source,
        },
    }


def _fetch_visualcrossing_weather_report(query: str, api_key: str) -> Dict[str, Any]:
    if not api_key:
        raise WeatherLookupError(
            "Visual Crossing requires an API key. Set `CLI_WEATHER_VISUALCROSSING_API_KEY` "
            "or run `cli-weather config set --visualcrossing-api-key ...`."
        )

    encoded_query = quote(query.strip(), safe="")
    params = urlencode(
        {
            "unitGroup": "us",
            "include": "current,days",
            "elements": (
                "datetime,tempmax,tempmin,precipprob,conditions,temp,feelslike,humidity,windspeed"
            ),
            "key": api_key,
            "contentType": "json",
        }
    )
    payload = _get_json(
        "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{encoded_query}?{params}"
    )
    current = payload.get("currentConditions") or {}
    days = payload.get("days") or []
    if not current or not days:
        raise WeatherLookupError("Visual Crossing did not return a complete forecast.")

    forecast = []
    for day in days[:7]:
        forecast.append(
            {
                "date": day["datetime"],
                "summary": day.get("conditions", "Unknown"),
                "high": round(day["tempmax"]),
                "low": round(day["tempmin"]),
                "precipitation_probability": round(day.get("precipprob", 0)),
            }
        )

    return {
        "location": payload.get("resolvedAddress") or query,
        "current": {
            "temperature": round(current["temp"]),
            "feels_like": round(current["feelslike"]),
            "humidity": round(current["humidity"]),
            "wind_speed": round(current["windspeed"]),
            "summary": current.get("conditions", "Unknown"),
        },
        "forecast": forecast,
        "sources": {
            "current": "Visual Crossing",
            "forecast": "Visual Crossing",
            "precipitation": "Visual Crossing",
        },
    }


def describe_weather_code(code: int) -> str:
    return WEATHER_CODES.get(code, f"Unknown conditions ({code})")


def format_weather_report(report: Dict[str, Any]) -> str:
    current = report["current"]
    forecast = report["forecast"]
    day_label_width = max(len(_format_day_label(day["date"])) for day in forecast)
    summary_width = max(len(day["summary"]) for day in forecast)
    lines = [
        report["location"],
        "",
        (
            f"Current: {current['temperature']}F, {current['summary']} "
            f"(feels like {current['feels_like']}F)"
        ),
        f"Humidity: {current['humidity']}%   Wind: {current['wind_speed']} mph",
        "",
        "7-Day Forecast",
    ]
    for day in forecast:
        precipitation = day["precipitation_probability"]
        day_label = _format_day_label(day["date"]).ljust(day_label_width)
        summary = day["summary"].ljust(summary_width)
        precipitation_parts = []
        if precipitation is not None:
            precipitation_parts.append(f"{precipitation}%")
        precipitation_amount = day.get("precipitation_amount_inches")
        if precipitation_amount:
            precipitation_parts.append(f"{precipitation_amount:.2f}in")
        precipitation_label = " / ".join(precipitation_parts) if precipitation_parts else "n/a"
        lines.append(
            f"{day_label}  {summary}  H:{day['high']}F  L:{day['low']}F  Rain:{precipitation_label}"
        )
    lines.extend(["", _format_source_line(report.get("sources", {}))])
    return "\n".join(lines)


def _format_day_label(date_text: str) -> str:
    day = datetime.strptime(date_text, "%Y-%m-%d")
    base_label = f"{day.strftime('%a %b')} {day.day}"
    today = date.today()
    if day.date() == today:
        return f"Today ({base_label})"
    if day.date() == today + timedelta(days=1):
        return f"Tomorrow ({base_label})"
    return base_label


def _extract_metno_period(data: Dict[str, Any]) -> Dict[str, Any]:
    for period_name in ("next_1_hours", "next_6_hours", "next_12_hours"):
        period = data.get(period_name, {})
        symbol_code = period.get("summary", {}).get("symbol_code")
        details = period.get("details", {})
        if symbol_code or details:
            return {
                "summary": _humanize_metno_symbol(symbol_code) if symbol_code else None,
                "precipitation_probability": details.get("probability_of_precipitation"),
                "precipitation_amount": details.get("precipitation_amount"),
            }
    return {
        "summary": None,
        "precipitation_probability": None,
        "precipitation_amount": None,
    }


def _humanize_metno_symbol(symbol_code: str) -> str:
    label = symbol_code
    for suffix in ("_day", "_night", "_polartwilight"):
        if label.endswith(suffix):
            label = label[: -len(suffix)]
            break
    return METNO_SYMBOLS.get(label, label.replace("_", " ").title())


def _celsius_to_fahrenheit(value: float) -> float:
    return (value * 9 / 5) + 32


def _meters_per_second_to_mph(value: float) -> float:
    return value * 2.23694


def _millimeters_to_inches(value: float) -> float:
    return value / 25.4


def _enrich_forecast_with_open_meteo_precipitation(
    location: Location,
    forecast: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], bool]:
    try:
        fallback_report = _fetch_open_meteo_weather_report_for_location(location)
    except WeatherLookupError:
        return forecast, False

    precipitation_by_date = {
        day["date"]: day.get("precipitation_probability")
        for day in fallback_report["forecast"]
        if day.get("precipitation_probability") is not None
    }
    used_fallback = False
    for day in forecast:
        if day.get("precipitation_probability") is None:
            fallback_probability = precipitation_by_date.get(day["date"])
            if fallback_probability is not None:
                day["precipitation_probability"] = fallback_probability
                used_fallback = True
    return forecast, used_fallback


def _format_source_line(sources: Dict[str, str]) -> str:
    current_source = sources.get("current", "Unknown")
    forecast_source = sources.get("forecast", current_source)
    precipitation_source = sources.get("precipitation", forecast_source)
    return (
        f"Sources: current {current_source}; "
        f"forecast {forecast_source}; "
        f"precipitation {precipitation_source}"
    )


def _result_matches_state(result: Dict[str, Any], state_code: str, state_name: str) -> bool:
    if result.get("country_code") != "US":
        return False
    admin1 = (result.get("admin1") or "").strip()
    admin1_code = (result.get("admin1_code") or "").strip()
    if admin1.lower() == state_name.lower():
        return True
    if admin1_code.upper() == state_code:
        return True
    if admin1_code.upper().endswith(f"-{state_code}"):
        return True
    return False


def _result_matches_country(result: Dict[str, Any], country_query: str) -> bool:
    country = (result.get("country") or "").strip().lower()
    country_code = (result.get("country_code") or "").strip().lower()
    if country == country_query:
        return True
    if country_code == country_query:
        return True
    return False
