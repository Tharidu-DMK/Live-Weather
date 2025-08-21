#!/usr/bin/env python3
import os
import logging
import requests
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- Config & Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment")
if not OPENWEATHER_API_KEY:
    raise RuntimeError("Missing OPENWEATHER_API_KEY in environment")

# ---------- Helpers ----------
def icon_for(condition: str) -> str:
    c = condition.lower()
    if "thunder" in c:
        return "⛈️"
    if "drizzle" in c:
        return "🌦️"
    if "rain" in c:
        return "🌧️"
    if "snow" in c:
        return "❄️"
    if "clear" in c:
        return "☀️"
    if "cloud" in c:
        return "☁️"
    if "mist" in c or "fog" in c or "haze" in c or "smoke" in c:
        return "🌫️"
    return "🌡️"

def fmt_time(ts: int, tz_offset_seconds: int) -> str:
    tz = timezone(timedelta(seconds=tz_offset_seconds))
    return datetime.fromtimestamp(ts, tz=tz).strftime("%a %d %b %H:%M")

def get_current_by_city(city: str, units: str = "metric") -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": units}
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def get_current_by_coords(lat: float, lon: float, units: str = "metric") -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": units}
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def get_forecast_by_coords(lat: float, lon: float, units: str = "metric") -> dict:
    # 5 day / 3-hour forecast
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": units, "cnt": 12}  # ~next 36 hours
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def format_current_weather(data: dict) -> str:
    name = data.get("name", "Your location")
    sys = data.get("sys", {})
    country = sys.get("country", "")
    weather = data["weather"][0]
    main = data["main"]
    wind = data.get("wind", {})
    icon = icon_for(weather["main"])

    tz_offset = data.get("timezone", 0)
    sunrise = sys.get("sunrise")
    sunset = sys.get("sunset")
    sunrise_str = fmt_time(sunrise, tz_offset) if sunrise else "N/A"
    sunset_str = fmt_time(sunset, tz_offset) if sunset else "N/A"

    lines = [
        f"{icon} *Current weather in {name}{', ' + country if country else ''}*",
        f"• {weather['description'].title()}",
        f"• Temp: {main['temp']:.1f}°C (feels {main['feels_like']:.1f}°C)",
        f"• Humidity: {main['humidity']}%  • Pressure: {main['pressure']} hPa",
        f"• Wind: {wind.get('speed', 0)} m/s",
        f"• Sunrise: {sunrise_str}  • Sunset: {sunset_str}",
    ]
    return "\n".join(lines)

def format_forecast(data: dict) -> str:
    city = data.get("city", {}).get("name", "location")
    country = data.get("city", {}).get("country", "")
    tz_offset = data.get("city", {}).get("timezone", 0)

    header = f"📅 *Next 36 hours for {city}{', ' + country if country else ''}*"
    entries = []
    for item in data.get("list", [])[:12]:
        ts = item["dt"]
        main = item["main"]
        weather = item["weather"][0]
        wind = item.get("wind", {})
        icon = icon_for(weather["main"])
        entries.append(
            f"{fmt_time(ts, tz_offset)} – {icon} {weather['description'].title()}, "
            f"{main['temp']:.0f}°C, wind {wind.get('speed', 0)} m/s"
        )

    return header + "\n" + "\n".join(f"• {line}" for line in entries)

# ---------- Bot Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = [[KeyboardButton("Send my location 📍", request_location=True)]]
    await update.message.reply_text(
        "Hi! I’m your Weather Bot.\n"
        "• Type /weather <city> (e.g. /weather Tokyo)\n"
        "• Or tap the button below to share your current location.\n"
        "Units: °C (metric).",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/weather <city> – Get weather for a city\n"
        "Share your location – Get weather for where you are\n"
        "/help – Show this help"
    )

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /weather <city name>\nExample: /weather Singapore")
        return

    city = " ".join(context.args)
    try:
        current = get_current_by_city(city, units="metric")
        lat = current["coord"]["lat"]
        lon = current["coord"]["lon"]
        forecast = get_forecast_by_coords(lat, lon, units="metric")

        current_text = format_current_weather(current)
        forecast_text = format_forecast(forecast)

        await update.message.reply_markdown(current_text)
        await update.message.reply_markdown(forecast_text)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            await update.message.reply_text("City not found. Try a different name or share your location.")
        else:
            logger.exception("HTTP error")
            await update.message.reply_text("Sorry, I couldn't fetch the weather right now.")
    except Exception:
        logger.exception("Unexpected error")
        await update.message.reply_text("Something went wrong. Please try again later.")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = update.message.location
    try:
        current = get_current_by_coords(loc.latitude, loc.longitude, units="metric")
        forecast = get_forecast_by_coords(loc.latitude, loc.longitude, units="metric")

        current_text = format_current_weather(current)
        forecast_text = format_forecast(forecast)

        await update.message.reply_markdown(current_text)
        await update.message.reply_markdown(forecast_text)
    except Exception:
        logger.exception("Location handling error")
        await update.message.reply_text("Couldn't fetch weather for that location. Try again.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I didn't understand that. Use /weather <city> or share your location.")

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
