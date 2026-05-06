from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
from weather_service import get_live_weather, get_weather_history, get_forecast
from model import WeatherMLModel
from recommendation import get_recommendation
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

model_path = os.path.join(os.path.dirname(__file__), 'weather_model.pkl')
dataset_path = os.path.join(os.path.dirname(__file__), 'dataset', 'weather_data.csv')
ml_model = WeatherMLModel(model_path=model_path)

# Initialize Model - Train if missing or load if exists
if not ml_model.load():
    print("Initializing system: Training ML model for the first time...")
    ml_model.train(dataset_path)
else:
    print("System Ready: AI Weather Model loaded successfully.")

def format_weather_for_ml(data):
    city = data.get("city", "Unknown")
    temp = data.get("temperature", 0)
    cond = data.get("condition", "unknown")
    hum = data.get("humidity", 0)
    return f"Weather report for {city}: Temperature is {temp}°C, condition is {cond}, and humidity is {hum}%."

def translate_to_english(text):
    if not text: return ""
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated
    except:
        return text

def extract_city(text):
    """
    Improved city extraction using regex and common patterns.
    """
    text = text.lower()
    # Common cities list (expanded)
    cities_list = [
        "vijayawada", "hyderabad", "chennai", "mumbai", "delhi", "kolkata", "bangalore", "pune", 
        "vizag", "guntur", "nellore", "kurnool", "tirupati", "warangal", "kochi", "patna", "jaipur", 
        "lucknow", "ahmedabad", "surat", "bhopal", "indore", "chandigarh", "amritsar", "london", 
        "new york", "tokyo", "paris", "berlin", "dubai", "singapore", "sydney", "rome", "madrid"
    ]
    
    # Try exact match from list
    for city in cities_list:
        if city in text:
            return city
    
    # Common English words that should NOT be treated as city names
    stop_words = {
        "should", "could", "would", "today", "tomorrow", "yesterday", "travel", "there",
        "going", "doing", "about", "these", "those", "their", "other", "which", "where",
        "when", "what", "have", "will", "been", "this", "that", "with", "from", "your",
        "they", "them", "than", "then", "also", "just", "like", "make", "know", "take",
        "come", "some", "time", "very", "much", "more", "only", "over", "such", "want",
        "give", "most", "tell", "wear", "safe", "help", "here", "good", "rain", "rain",
        "cold", "warm", "cool", "wind", "heat", "haze", "snow", "real", "fake",
        "outside", "inside", "outdoor", "morning", "evening", "night", "afternoon",
        "weather", "climate", "forecast", "report", "alert", "warning", "degree",
        "sunny", "rainy", "cloudy", "foggy", "windy", "stormy", "humid", "drive",
        "flight", "walking", "jogging", "hiking", "running", "outing", "event",
    }
            
    # Try pattern matching: "in {City}", "at {City}", "for {City}"
    patterns = [r"in\s+([a-z]+)", r"at\s+([a-z]+)", r"for\s+([a-z]+)", r"to\s+([a-z]+)"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            potential_city = match.group(1)
            if len(potential_city) > 3 and potential_city not in stop_words:
                return potential_city
                
    return None

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    mode = data.get('mode', 'auto')
    original_text = data.get('text', '')
    text = translate_to_english(original_text) if mode == 'manual' else original_text
    
    if mode == 'manual':
        detected_city = extract_city(text)
        weather_data = get_live_weather(detected_city) if detected_city else {}
        
        result = ml_model.predict(text=text, weather_data=weather_data)
        result['detected_city'] = detected_city
        result['feels_like'] = weather_data.get('feels_like', weather_data.get('temperature', 35))
        result['humidity'] = weather_data.get('humidity', 50)
        result['wind_speed'] = weather_data.get('wind_speed', 0)
        result['timestamp'] = weather_data.get('timestamp', 'Live')
        
        from recommendation import manual_recommendation
        result['recommendation'] = manual_recommendation(text, result['prediction'])
        result['original_text'] = original_text
        result['translated_text'] = text
        return jsonify(result)
    else:
        city = data.get('city', 'Vijayawada')
        weather_data = get_live_weather(city)
        if not weather_data.get("success"):
            return jsonify({"error": "Failed to fetch weather"}), 500
            
        weather_text = format_weather_for_ml(weather_data)
        result = ml_model.predict(text=weather_text, weather_data=weather_data)
        result['weather_data'] = weather_data
        result['recommendation'] = get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"])
        return jsonify(result)

chat_memory = {"last_city": "hyderabad"}

def _flag_response(reason):
    """Return a flagged response for inappropriate or off-topic queries."""
    return jsonify({
        "response": f"🚩 **Flagged**: {reason}\n\nI'm an AI Weather Intelligence Assistant. I can only help with weather-related queries such as:\n• Current weather & forecasts\n• Rain, storm & safety alerts\n• Travel & outdoor planning\n• Clothing recommendations\n• Climate trends & history\n\nPlease ask me something weather-related!"
    })

def _build_full_weather_report(weather_data, city):
    """Build a comprehensive weather report string."""
    temp = weather_data.get("temperature", "N/A")
    feels = weather_data.get("feels_like", temp)
    cond = weather_data.get("condition", "unknown").capitalize()
    hum = weather_data.get("humidity", "N/A")
    wind = weather_data.get("wind_speed", "N/A")
    source = weather_data.get("source", "Verified Feed")
    ts = weather_data.get("timestamp", "Live")

    resp = f"🌍 Live Weather Report — {city.capitalize()}\n"
    resp += f"------------------\n"
    resp += f"🌡️ Temperature: {temp}°C (Feels like {feels}°C)\n"
    resp += f"☁️ Condition: {cond}\n"
    resp += f"💧 Humidity: {hum}%\n"
    resp += f"💨 Wind Speed: {wind} m/s\n"
    resp += f"📶 Source: {source} | 🕒 {ts}"
    return resp

def _is_weather_related(query):
    """Check if a query is related to weather or climate topics."""
    weather_keywords = [
        "weather", "temperature", "temp", "rain", "rainy", "raining", "storm", "stormy",
        "thunder", "lightning", "snow", "snowing", "fog", "foggy", "mist", "misty",
        "cloud", "cloudy", "sunny", "sun", "wind", "windy", "breeze", "humid", "humidity",
        "hot", "cold", "warm", "cool", "heat", "freeze", "freezing", "chill", "chilly",
        "flood", "flooding", "cyclone", "hurricane", "tornado", "typhoon", "drought",
        "monsoon", "hail", "hailstorm", "dew", "frost", "ice", "icy",
        "climate", "season", "summer", "winter", "spring", "autumn", "fall",
        "uv", "ultraviolet", "sunburn", "sunscreen", "pollution", "air quality", "aqi",
        "forecast", "prediction", "tomorrow", "yesterday", "today", "tonight", "morning",
        "afternoon", "evening", "week", "weekend",
        "umbrella", "raincoat", "jacket", "sweater", "sunglasses",
        "outdoor", "travel", "trip", "picnic", "hike", "hiking", "jogging", "walk",
        "drive", "driving", "commute", "flight", "fly",
        "wear", "cloth", "dress", "outfit", "recommend",
        "safe", "safety", "danger", "dangerous", "risk", "alert", "warning",
        "degree", "celsius", "fahrenheit", "pressure", "barometer",
        "visibility", "sunrise", "sunset", "feels like",
        "compare", "difference", "versus", "vs", "better", "worse", "hotter", "colder",
        "fake", "real", "genuine", "hoax", "rumor", "rumour", "verify", "check",
        "city", "area", "region", "place", "location"
    ]
    return any(kw in query for kw in weather_keywords)

@app.route('/agent', methods=['POST'])
def ai_agent():
    global chat_memory
    user_query_original = request.json.get('query', '')
    user_query = translate_to_english(user_query_original).lower().strip()

    # ── Guard: empty query ──
    if not user_query:
        return jsonify({"response": "Please type a question about weather and I'll help you out! 🌤️"})

    # ── Greetings ──
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening",
                 "how are you", "what's up", "sup", "howdy", "namaste", "hola"]
    if any(user_query.strip() == g or user_query.startswith(g + " ") or user_query.startswith(g + ",") for g in greetings):
        return jsonify({"response": "👋 Hello! I'm your AI Weather Intelligence Assistant.\n\nHere's what I can do:\n• 🌡️ Live weather for any city\n• 🌧️ Rain & storm risk analysis\n• 📊 48-hour trends & forecasts\n• 👕 Clothing & lifestyle advice\n• ✈️ Travel weather planning\n• 🔍 Fake alert detection\n\nJust ask me anything weather-related!"})

    # ── Thank you / goodbye ──
    if any(x in user_query for x in ["thank", "thanks", "bye", "goodbye", "see you", "take care"]):
        return jsonify({"response": "😊 You're welcome! Stay safe and weather-aware. Feel free to come back anytime! 👋"})

    # ── Help / what can you do ──
    if any(x in user_query for x in ["help", "what can you do", "what do you do", "your features", "capabilities"]):
        return jsonify({"response": "🤖 I'm your AI Weather Intelligence Assistant! Here's what I can help with:\n\n🌡️ **Live Weather** — \"What's the weather in Mumbai?\"\n🌧️ **Rain Check** — \"Will it rain in Chennai today?\"\n📊 **Trends** — \"Show me forecast for Delhi\"\n👕 **Advice** — \"What should I wear in Bangalore?\"\n✈️ **Travel** — \"Is it safe to travel to Hyderabad?\"\n🔍 **Verify Alerts** — \"Is this storm warning real?\"\n🌡️ **Compare** — \"Is Mumbai hotter than Delhi?\"\n\nJust type any weather question!"})

    # ── Flag: Inappropriate / harmful / off-topic content ──
    flagged_patterns = [
        "hack", "kill", "bomb", "attack", "porn", "sex", "nude", "drug",
        "suicide", "murder", "abuse", "racist", "terrorism", "weapon",
        "gambling", "casino", "bitcoin", "crypto", "stock market",
        "write code", "programming", "python", "javascript",
        "movie", "song", "game", "football", "cricket score",
        "recipe", "cook", "food", "restaurant",
        "relationship", "dating", "girlfriend", "boyfriend",
        "homework", "exam", "math", "science", "history of india",
        "politics", "election", "minister", "president"
    ]
    if any(p in user_query for p in flagged_patterns) and not _is_weather_related(user_query):
        return _flag_response("Your question doesn't appear to be weather-related.")

    # ── City Detection ──
    current_mentioned_city = extract_city(user_query)
    if current_mentioned_city:
        chat_memory["last_city"] = current_mentioned_city

    effective_city = chat_memory["last_city"]
    weather_data = get_live_weather(effective_city)
    temp = weather_data.get("temperature", 0)
    humidity = weather_data.get("humidity", 0)
    condition = weather_data.get("condition", "").lower()
    wind = weather_data.get("wind_speed", 0)
    feels_like = weather_data.get("feels_like", temp)

    # ── Compare two cities ──
    if any(x in user_query for x in ["compare", "vs", "versus", "hotter", "colder", "warmer", "cooler", "difference"]):
        # Try to find two cities
        cities_found = []
        for city in ["vijayawada", "hyderabad", "chennai", "mumbai", "delhi", "kolkata", "bangalore", "pune",
                      "vizag", "guntur", "kochi", "jaipur", "lucknow", "ahmedabad", "london", "new york",
                      "tokyo", "paris", "dubai", "singapore", "sydney"]:
            if city in user_query:
                cities_found.append(city)
        if len(cities_found) >= 2:
            w1 = get_live_weather(cities_found[0])
            w2 = get_live_weather(cities_found[1])
            t1, t2 = w1.get("temperature", 0), w2.get("temperature", 0)
            diff = abs(t1 - t2)
            hotter = cities_found[0] if t1 > t2 else cities_found[1]
            resp = f"🔄 Weather Comparison\n------------------\n"
            resp += f"📍 {cities_found[0].capitalize()}: {t1}°C — {w1.get('condition', 'N/A').capitalize()}\n"
            resp += f"📍 {cities_found[1].capitalize()}: {t2}°C — {w2.get('condition', 'N/A').capitalize()}\n\n"
            resp += f"🌡️ {hotter.capitalize()} is warmer by {round(diff, 1)}°C."
            return jsonify({"response": resp})
        # Single city comparison falls through to general weather

    # ── Forecast / history / tomorrow / yesterday ──
    if any(x in user_query for x in ["forecast", "tomorrow", "next", "upcoming", "predict", "prediction",
                                       "yesterday", "last", "history", "trend", "past", "previous"]):
        history_data = get_weather_history(effective_city, current_temp=temp)
        history, _ = history_data

        resp = f"📊 Weather Trend — {effective_city.capitalize()}\n------------------\n"
        for item in history:
            resp += f"• {item['day']}: {item['temperature']}°C ({item['condition'].capitalize()})\n"
        resp += f"• Today: {temp}°C ({condition.capitalize()})\n"

        if humidity > 70:
            resp += f"\n🚨 Alert: High humidity ({humidity}%) — rain is likely."
        elif humidity > 50:
            resp += f"\n⚠️ Moderate humidity ({humidity}%) — slight chance of rain."
        else:
            resp += f"\n✅ Conditions appear stable for {effective_city.capitalize()}."
        return jsonify({"response": resp})

    # ── Rain / precipitation questions ──
    if any(x in user_query for x in ["rain", "raining", "rainy", "precipitation", "drizzle", "shower",
                                       "umbrella", "wet", "pour", "pouring"]):
        rain_conds = ["rain", "drizzle", "shower", "thunderstorm", "storm"]
        is_rainy = any(r in condition for r in rain_conds)
        high_humidity = humidity > 70

        if is_rainy:
            resp = f"🌧️ Yes! It is currently raining in {effective_city.capitalize()}.\n"
            resp += f"• Condition: {condition.capitalize()}\n"
            resp += f"• Humidity: {humidity}%\n"
            resp += f"☂️ Carry an umbrella and avoid open areas."
        elif high_humidity:
            resp = f"⚠️ No rain right now in {effective_city.capitalize()}, but humidity is high ({humidity}%).\n"
            resp += f"• Condition: {condition.capitalize()}\n"
            resp += f"🌂 Rain is possible — carrying an umbrella would be wise."
        else:
            resp = f"☀️ No rain expected in {effective_city.capitalize()} right now.\n"
            resp += f"• Condition: {condition.capitalize()}\n"
            resp += f"• Humidity: {humidity}%\n"
            resp += f"✅ Skies look clear. No umbrella needed!"
        return jsonify({"response": resp})

    # ── Storm / severe weather / safety ──
    if any(x in user_query for x in ["storm", "thunder", "lightning", "cyclone", "hurricane", "tornado",
                                       "typhoon", "severe", "danger", "dangerous", "safe", "safety",
                                       "flood", "flooding", "warning", "alert", "emergency"]):
        severe_conds = ["storm", "thunder", "lightning", "cyclone", "hurricane", "tornado"]
        is_severe = any(s in condition for s in severe_conds)

        if is_severe:
            resp = f"🚨 SEVERE WEATHER ALERT — {effective_city.capitalize()}\n------------------\n"
            resp += f"⚠️ Current: {condition.capitalize()}\n"
            resp += f"💨 Wind: {wind} m/s | 💧 Humidity: {humidity}%\n\n"
            resp += f"🛑 Safety advice:\n• Stay indoors and avoid travel\n• Keep away from windows\n• Follow official local alerts"
        elif wind > 10:
            resp = f"⚠️ High winds detected in {effective_city.capitalize()} ({wind} m/s).\n"
            resp += f"Exercise caution if travelling. Otherwise, conditions are manageable."
        else:
            resp = f"✅ No severe weather detected in {effective_city.capitalize()}.\n"
            resp += f"• Condition: {condition.capitalize()}\n"
            resp += f"• Wind: {wind} m/s | Humidity: {humidity}%\n"
            resp += f"Conditions are safe for normal activities."
        return jsonify({"response": resp})

    # ── Temperature / hot / cold questions ──
    if any(x in user_query for x in ["temperature", "temp", "hot", "cold", "warm", "cool", "heat",
                                       "chill", "chilly", "freeze", "freezing", "degree",
                                       "celsius", "fahrenheit", "feels like", "thermal"]):
        resp = f"🌡️ Temperature Report — {effective_city.capitalize()}\n------------------\n"
        resp += f"• Current: {temp}°C\n"
        resp += f"• Feels Like: {feels_like}°C\n"
        resp += f"• Condition: {condition.capitalize()}\n\n"

        if temp >= 40:
            resp += "🔴 Extreme heat! Stay indoors, hydrate frequently, and avoid direct sun."
        elif temp >= 35:
            resp += "🟠 Very hot conditions. Limit outdoor exposure and drink plenty of water."
        elif temp >= 30:
            resp += "🟡 Warm weather. Light clothing recommended. Stay hydrated."
        elif temp >= 20:
            resp += "🟢 Pleasant temperature. Great for outdoor activities!"
        elif temp >= 10:
            resp += "🔵 Cool weather. A light jacket is recommended."
        else:
            resp += "❄️ Cold conditions. Bundle up with warm layers!"
        return jsonify({"response": resp})

    # ── Humidity / moisture ──
    if any(x in user_query for x in ["humid", "humidity", "moisture", "muggy", "sticky", "damp", "dry"]):
        resp = f"💧 Humidity Report — {effective_city.capitalize()}\n------------------\n"
        resp += f"• Humidity: {humidity}%\n"
        resp += f"• Temperature: {temp}°C | Feels Like: {feels_like}°C\n\n"
        if humidity > 80:
            resp += "🌊 Very high humidity. Expect muggy, uncomfortable conditions. Rain is very likely."
        elif humidity > 60:
            resp += "💦 Moderately humid. You may feel sticky outdoors. Carry water."
        elif humidity > 40:
            resp += "✅ Comfortable humidity levels. Good for most activities."
        else:
            resp += "🏜️ Low humidity. Air is dry — stay hydrated and use moisturizer."
        return jsonify({"response": resp})

    # ── Wind ──
    if any(x in user_query for x in ["wind", "windy", "breeze", "gust", "breezy"]):
        resp = f"💨 Wind Report — {effective_city.capitalize()}\n------------------\n"
        resp += f"• Wind Speed: {wind} m/s\n"
        resp += f"• Condition: {condition.capitalize()}\n\n"
        if wind > 15:
            resp += "🚨 Strong winds! Avoid outdoor activities and secure loose objects."
        elif wind > 8:
            resp += "⚠️ Moderate to strong wind. Be cautious while driving or cycling."
        elif wind > 3:
            resp += "🍃 Light breeze. Pleasant conditions for outdoor activities."
        else:
            resp += "😌 Calm winds. Very peaceful weather."
        return jsonify({"response": resp})

    # ── Travel / outdoor / commute ──
    if any(x in user_query for x in ["travel", "trip", "journey", "commute", "drive", "driving", "fly",
                                       "flight", "outdoor", "outside", "picnic", "hike", "hiking",
                                       "jogging", "walk", "walking", "run", "running", "exercise",
                                       "go out", "go outside", "step out", "outing", "event"]):
        resp = f"✈️ Travel & Outdoor Advisory — {effective_city.capitalize()}\n------------------\n"
        resp += f"🌡️ {temp}°C (Feels like {feels_like}°C) | {condition.capitalize()}\n"
        resp += f"💧 Humidity: {humidity}% | 💨 Wind: {wind} m/s\n\n"

        issues = []
        if any(r in condition for r in ["rain", "storm", "thunder"]):
            issues.append("🌧️ Rain/storms detected — carry rain gear")
        if temp >= 38:
            issues.append("🔥 Extreme heat — carry water & sunscreen")
        if wind > 10:
            issues.append("💨 High winds — be cautious")
        if humidity > 80:
            issues.append("💦 Very humid — you'll sweat a lot")

        if issues:
            resp += "⚠️ Things to watch out for:\n" + "\n".join(f"  {i}" for i in issues)
        else:
            resp += "✅ Weather looks great for outdoor activities! Enjoy your day."
        return jsonify({"response": resp})

    # ── Clothing / what to wear ──
    if any(x in user_query for x in ["wear", "cloth", "dress", "outfit", "attire", "jacket", "sweater",
                                       "raincoat", "sunglasses", "sunscreen", "hat", "cap"]):
        advice = get_recommendation(temp, condition, humidity)
        return jsonify({"response": f"👕 Clothing Advice — {effective_city.capitalize()}\n------------------\n🌡️ {temp}°C | {condition.capitalize()}\n\n{advice}"})

    # ── Fake/real alert verification ──
    if any(x in user_query for x in ["fake", "real", "genuine", "hoax", "rumor", "rumour", "verify",
                                       "check alert", "is this true", "believe", "trust"]):
        resp = f"🔍 Alert Verification — {effective_city.capitalize()}\n------------------\n"
        resp += f"Current verified data: {temp}°C, {condition.capitalize()}, {humidity}% humidity\n\n"
        resp += "To verify a weather alert:\n"
        resp += "1️⃣ Switch to **Manual Mode** above\n"
        resp += "2️⃣ Paste the suspicious alert text\n"
        resp += "3️⃣ Our ML model will analyze it and give a Real/Fake verdict with confidence score\n\n"
        resp += "💡 Tip: Always cross-check weather alerts with official meteorological services."
        return jsonify({"response": resp})

    # ── Sunrise / sunset / time-related ──
    if any(x in user_query for x in ["sunrise", "sunset", "dawn", "dusk", "night", "daytime",
                                       "morning weather", "evening weather", "tonight"]):
        import datetime
        hour = datetime.datetime.now().hour
        if hour < 6:
            time_ctx = "It's currently nighttime 🌙"
        elif hour < 12:
            time_ctx = "It's currently morning 🌅"
        elif hour < 17:
            time_ctx = "It's currently afternoon ☀️"
        elif hour < 20:
            time_ctx = "It's currently evening 🌇"
        else:
            time_ctx = "It's currently night 🌙"

        resp = f"🕐 Time-based Weather — {effective_city.capitalize()}\n------------------\n"
        resp += f"{time_ctx}\n"
        resp += f"🌡️ {temp}°C (Feels like {feels_like}°C)\n"
        resp += f"☁️ {condition.capitalize()} | 💧 {humidity}%\n\n"
        resp += "📝 Note: Exact sunrise/sunset times depend on your local timezone and season."
        return jsonify({"response": resp})

    # ── General weather query (broad catch) ──
    if _is_weather_related(user_query) or current_mentioned_city:
        if weather_data.get("success"):
            return jsonify({"response": _build_full_weather_report(weather_data, effective_city)})
        else:
            return jsonify({"response": f"Sorry, I couldn't fetch weather data for {effective_city.capitalize()}. Please try again or check the city name."})

    # ── Final fallback: flag as off-topic ──
    return _flag_response("Your question doesn't appear to be weather-related.")

@app.route('/history', methods=['GET'])
def weather_history():
    city = request.args.get('city', 'Vijayawada')
    weather_data = get_live_weather(city)
    history, current_temp = get_weather_history(city, current_temp=weather_data.get("temperature"))
    return jsonify({
        "history": history,
        "current_temp": current_temp
    })

@app.route('/live-weather', methods=['GET'])
def live_weather():
    city = request.args.get('city', 'Vijayawada')
    weather_data = get_live_weather(city)
    if not weather_data.get("success"):
        return jsonify({"error": "Failed to fetch"}), 500
    
    weather_text = format_weather_for_ml(weather_data)
    ml_result = ml_model.predict(text=weather_text, weather_data=weather_data)
    
    return jsonify({
        "city": weather_data["city"],
        "temperature": weather_data["temperature"],
        "feels_like": weather_data.get("feels_like", weather_data["temperature"]),
        "weather": weather_data["condition"],
        "humidity": weather_data["humidity"],
        "wind_speed": weather_data.get("wind_speed", 0),
        "prediction": ml_result["prediction"],
        "confidence": ml_result["confidence"],
        "explanation": ml_result["explanation"],
        "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"]),
        "source": weather_data["source"],
        "timestamp": weather_data.get("timestamp", ""),
        "mock": weather_data.get("mock", False)
    })

@app.route('/auto-feed', methods=['GET'])
def auto_feed():
    cities = ["Vijayawada", "Hyderabad", "Chennai", "Mumbai"]
    results = []
    for city in cities:
        weather_data = get_live_weather(city)
        if weather_data.get("success"):
            weather_text = format_weather_for_ml(weather_data)
            ml_result = ml_model.predict(text=weather_text, weather_data=weather_data)
            results.append({
                "city": weather_data["city"],
                "temperature": weather_data["temperature"],
                "feels_like": weather_data.get("feels_like", weather_data["temperature"]),
                "weather": weather_data["condition"],
                "prediction": ml_result["prediction"],
                "confidence": ml_result["confidence"],
                "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"]),
                "source": weather_data["source"],
                "timestamp": weather_data.get("timestamp", "")
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
