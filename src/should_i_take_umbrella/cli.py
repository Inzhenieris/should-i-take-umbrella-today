from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
USER_MENTION = os.getenv("DISCORD_MENTION", "<@504997242525188099>")


@dataclass(frozen=True)
class Window:
    label: str
    start: time
    end: time


def env_time(name: str, default: str) -> time:
    return time.fromisoformat(os.getenv(name, default))


def build_windows() -> list[Window]:
    return [
        Window("morning commute", env_time("MORNING_START", "07:00"), env_time("MORNING_END", "09:30")),
        Window("evening commute", env_time("EVENING_START", "16:30"), env_time("EVENING_END", "18:30")),
    ]


def fetch_forecast(client: httpx.Client, timezone: str, latitude: str, longitude: str) -> dict:
    response = client.get(
        OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "hourly": "precipitation_probability,precipitation",
            "forecast_days": 1,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def parse_hourly(forecast: dict) -> dict[datetime, dict[str, float]]:
    hourly = forecast["hourly"]
    result: dict[datetime, dict[str, float]] = {}
    for stamp, probability, precipitation in zip(
        hourly["time"],
        hourly["precipitation_probability"],
        hourly["precipitation"],
        strict=True,
    ):
        result[datetime.fromisoformat(stamp)] = {
            "probability": float(probability or 0),
            "precipitation": float(precipitation or 0),
        }
    return result


def window_hits(
    hourly: dict[datetime, dict[str, float]],
    timezone: str,
    day: date,
    window: Window,
) -> list[tuple[datetime, dict[str, float]]]:
    hits: list[tuple[datetime, dict[str, float]]] = []
    tz = ZoneInfo(timezone)
    for stamp, values in hourly.items():
        local_stamp = stamp.replace(tzinfo=tz)
        if local_stamp.date() != day:
            continue
        if window.start <= local_stamp.time() <= window.end and (
            values["precipitation"] > 0 or values["probability"] > 0
        ):
            hits.append((local_stamp, values))
    return hits


def build_weather_message(
    day: date,
    timezone: str,
    hits_by_window: dict[str, list[tuple[datetime, dict[str, float]]]],
) -> str:
    lines = [f"☔ {USER_MENTION} umbrella check for {day.isoformat()} ({timezone})"]
    rainy = False
    for label, hits in hits_by_window.items():
        if not hits:
            lines.append(f"- {label}: no rain expected")
            continue
        rainy = True
        parts = []
        for stamp, values in hits:
            parts.append(
                f"{stamp.strftime('%H:%M')} ({int(values['probability'])}% / {values['precipitation']:.1f} mm)"
            )
        lines.append(f"- {label}: rain possible at {', '.join(parts)}")
    if rainy:
        lines.append("Take umbrella.")
    else:
        lines.append("No umbrella needed based on current forecast.")
    return "\n".join(lines)


def build_status_message(stage: str, details: str | None = None) -> str:
    message = f"🟢 umbrella bot {stage}"
    if details:
        message = f"{message}\n{details}"
    return message


def post_to_discord(client: httpx.Client, webhook_url: str, content: str) -> None:
    response = client.post(webhook_url, json={"content": content}, timeout=30.0)
    response.raise_for_status()


def run_check(client: httpx.Client, webhook_url: str) -> str:
    timezone = os.getenv("TIMEZONE", "Europe/Riga")
    latitude = os.getenv("LATITUDE", "56.9496")
    longitude = os.getenv("LONGITUDE", "24.1052")
    today = datetime.now(ZoneInfo(timezone)).date()
    windows = build_windows()

    forecast = fetch_forecast(client, timezone, latitude, longitude)
    hourly = parse_hourly(forecast)
    hits_by_window = {
        window.label: window_hits(hourly, timezone, today, window)
        for window in windows
    }
    content = build_weather_message(today, timezone, hits_by_window)
    post_to_discord(client, webhook_url, content)
    return content


def main() -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise SystemExit("DISCORD_WEBHOOK_URL is required")

    with httpx.Client() as client:
        post_to_discord(client, webhook_url, build_status_message("startup"))
        try:
            content = run_check(client, webhook_url)
            post_to_discord(client, webhook_url, build_status_message("shutdown", "Run completed successfully."))
            print(json.dumps({"posted": True, "content": content}, ensure_ascii=False))
        except Exception as exc:
            post_to_discord(
                client,
                webhook_url,
                build_status_message("shutdown", f"Run failed: {type(exc).__name__}: {exc}"),
            )
            raise


if __name__ == "__main__":
    main()
