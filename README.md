# Live-Weather
simple telegram weather bot that shows current weather and a 36-hour forecast by city name or your shared location.

## Features
- `/weather <city>` for city-based weather
- Share your location for hyper-local weather
- Current conditions + next 36 hours (5-day/3-hour API, first 12 entries)
- Pretty formatting and emojis
- Uses OpenWeather (free plan works)

## Quick Start
1. Create a bot via **@BotFather** and copy the bot token.
2. Get an API key from **https://openweathermap.org/** (free tier is fine).
3. Create a `.env` file from `.env.example` and fill your keys.
4. Install deps and run:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Talk to your bot on Telegram. Try: `/weather Singapore` or send your location.

## Deploy with Docker
```bash
docker build -t telegram-weather-bot .
docker run -e TELEGRAM_BOT_TOKEN=xxx -e OPENWEATHER_API_KEY=yyy telegram-weather-bot
```

## Notes
- This example uses long polling. For webhooks, host a small web server or use a platform like Render/Railway.
- Respect API rate limits and cache responses if you expect heavy use.
