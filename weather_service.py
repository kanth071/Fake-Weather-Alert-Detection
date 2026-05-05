import requests
import os
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from the absolute path of this script
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not API_KEY:
    logger.error("CRITICAL: OPENWEATHER_API_KEY not found in environment!")
else:
    # Redact most of the key for security in logs
    redacted_key = API_KEY[:4] + "*" * (len(API_KEY) - 8) + API_KEY[-4:]
    logger.info(f"API Key detected: {redacted_key}")

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# In-memory caches to ensure data consistency and prevent "jumping" values
history_cache = {}
live_cache = {}
forecast_cache = {}

def get_live_weather(city):
    if not city:
        return {"success": False, "error": "No city provided"}
        
    city_key = city.lower().strip()
    
    # Check cache first (valid for 10 minutes)
    if city_key in live_cache:
        cached_data, timestamp = live_cache[city_key]
        if time.time() - timestamp < 600:
            logger.info(f"Returning cached weather for {city}")
            return cached_data

    # Attempt Real API Call
    if API_KEY:
        try:
            logger.info(f"Fetching real-time weather for {city} from OpenWeather...")
            params = {"q": city, "appid": API_KEY, "units": "metric"}
            response = requests.get(BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "city": data["name"],
                    "temperature": round(data["main"]["temp"], 1),
                    "condition": data["weather"][0]["description"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                    "success": True,
                    "source": "OpenWeather Verified API",
                    "mock": False
                }
                live_cache[city_key] = (result, time.time())
                return result
            elif response.status_code == 401:
                logger.warning(f"Invalid API Key for OpenWeather.")
            elif response.status_code == 404:
                logger.warning(f"City '{city}' not found.")
            else:
                logger.warning(f"API Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"API Error fetching weather: {e}")

    # Fallback to Stable Mock Data
    logger.info(f"Falling back to mock weather for {city}")
    result = get_mock_weather(city)
    live_cache[city_key] = (result, time.time())
    return result

def get_forecast(city):
    city_key = city.lower().strip()
    
    if city_key in forecast_cache:
        cached_data, timestamp = forecast_cache[city_key]
        if time.time() - timestamp < 1800: # 30 minute stability for forecast
            return cached_data

    if API_KEY:
        try:
            logger.info(f"Fetching 5-day forecast for {city} from OpenWeather...")
            params = {"q": city, "appid": API_KEY, "units": "metric"}
            response = requests.get(FORECAST_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                forecast_list = data["list"]
                processed_forecast = []
                
                for i in range(0, min(len(forecast_list), 40), 8):
                    item = forecast_list[i]
                    processed_forecast.append({
                        "day": time.strftime('%a', time.gmtime(item['dt'])),
                        "temperature": round(item['main']['temp'], 1),
                        "condition": item['weather'][0]['description']
                    })
                
                forecast_cache[city_key] = (processed_forecast, time.time())
                return processed_forecast
        except Exception as e:
            logger.error(f"Forecast API Error: {e}")
            
    return None

def get_weather_history(city, current_temp=None):
    city_key = city.lower().strip()
    forecast = get_forecast(city)
    
    import random
    random.seed(city_key + "_hist")
    # Use a more realistic base temp if current_temp is missing
    base_temp = current_temp if current_temp is not None else 32
    yesterday_temp = base_temp + random.uniform(-2, 2)
    random.seed()

    history_item = {
        "day": "Yesterday",
        "temperature": round(yesterday_temp, 1),
        "condition": "scattered clouds"
    }

    tomorrow_item = {
        "day": "Tomorrow",
        "temperature": round(base_temp + 1, 1),
        "condition": "clear sky"
    }
    
    if forecast and len(forecast) > 1:
        tomorrow_item = {
            "day": "Tomorrow",
            "temperature": forecast[1]["temperature"],
            "condition": forecast[1]["condition"]
        }

    return [history_item, tomorrow_item], current_temp

def get_mock_weather(city):
    import random
    random.seed(city.lower().strip())
    
    conditions = ["clear sky", "few clouds", "scattered clouds", "broken clouds", "shower rain", "rain", "thunderstorm"]
    city_hash = sum(ord(c) for c in city)
    # Defaulting mock data to a warmer range (25-42°C) to match user's expected climate
    base_temp = 25 + (city_hash % 17) 
    temp = base_temp + random.uniform(-1, 1)
    humidity = 40 + (city_hash % 45)
    
    random.seed()
    
    return {
        "city": city.capitalize(),
        "temperature": round(temp, 1),
        "condition": random.choice(conditions),
        "humidity": humidity,
        "success": True,
        "source": "AI Simulation Engine (Fallback)",
        "mock": True
    }
