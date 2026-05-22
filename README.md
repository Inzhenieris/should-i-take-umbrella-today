# should-i-take-umbrella-today

Small Python automation that checks the Riga forecast and posts to Discord if you should take an umbrella.

## What it does

Every morning it checks Open-Meteo for Riga and looks for rain in two windows:
- morning commute: 07:00 to 09:30 Europe/Riga
- evening commute: 16:30 to 18:30 Europe/Riga

If rain is expected in either window, it posts a message to Discord.

## Environment variables

- `DISCORD_WEBHOOK_URL` - Discord webhook for the `should-i-take-umbrella` channel
- `LATITUDE` - default `56.9496`
- `LONGITUDE` - default `24.1052`
- `TIMEZONE` - default `Europe/Riga`
- `MORNING_START` - default `07:00`
- `MORNING_END` - default `09:30`
- `EVENING_START` - default `16:30`
- `EVENING_END` - default `18:30`

## Run locally

```bash
uv sync
uv run umbrella-check
```

## Docker

```bash
docker build -t should-i-take-umbrella-today .
docker run --rm \
  -e DISCORD_WEBHOOK_URL=... \
  should-i-take-umbrella-today
```

## Scheduling

Run once per day at 06:30 Europe/Riga using your scheduler of choice, for example cron, GitHub Actions schedule, or a container platform scheduler.
