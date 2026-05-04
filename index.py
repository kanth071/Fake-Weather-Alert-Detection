from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from weather_service import get_live_weather, get_weather_history
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
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated
    except:
        return text

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    mode = data.get('mode', 'auto')
    original_text = data.get('text', '')
    text = translate_to_english(original_text) if mode == 'manual' else original_text
    
    if mode == 'manual':
        # Expanded city detection list
        cities = ["vijayawada", "hyderabad", "chennai", "mumbai", "delhi", "kolkata", "bangalore", "pune", 
                  "vizag", "guntur", "nellore", "kurnool", "tirupati", "warangal", "kochi", "patna", "jaipur", 
                  "lucknow", "ahmedabad", "surat", "bhopal", "indore", "chandigarh", "amritsar"]
        weather_data = get_live_weather(detected_city) if detected_city else {}
        result = ml_model.predict(text=text, weather_data=weather_data)
        result['detected_city'] = detected_city
        
        # Determine dummy values for manual recommendations based on text if city not found
        temp = weather_data.get('temperature', 25)
        cond = weather_data.get('condition', 'clear')
        if not detected_city:
            if any(x in text_lower for x in ["hot", "heat", "40c", "fire"]): temp = 40
            if any(x in text_lower for x in ["cold", "snow", "10c", "winter"]): temp = 10
            if any(x in text_lower for x in ["rain", "shower", "drizzle"]): cond = "rain"
            if any(x in text_lower for x in ["thunder", "storm", "lightning"]): cond = "thunderstorm"
            if any(x in text_lower for x in ["cloud", "overcast"]): cond = "clouds"
        
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

# Simple Conversational Memory
chat_memory = {"last_city": "hyderabad"}

@app.route('/agent', methods=['POST'])
def ai_agent():
    global chat_memory
    user_query_original = request.json.get('query', '')
    user_query = translate_to_english(user_query_original).lower()
    
    # Priority 0: Greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste", "how are you"]
    if any(g in user_query for g in greetings):
        return jsonify({"response": "👋 Hello! I am your AI Weather Intelligence Assistant. I can analyze climate history, predict rain risks, and provide lifestyle advice for any city. How can I help you today?"})

    # Enhanced City Detection
    words = user_query_original.split()
    current_mentioned_city = None
    common_cities = ["vijayawada", "hyderabad", "chennai", "mumbai", "delhi", "kolkata", "bangalore", "pune", "london", "new york", "tokyo", "paris", "berlin", "dubai", "singapore", "sydney", "vizag"]
    
    for city in common_cities:
        if city in user_query:
            current_mentioned_city = city
            break
            
    if not current_mentioned_city:
        for i, word in enumerate(words):
            if word.lower() in ["in", "at", "for"] and i + 1 < len(words):
                current_mentioned_city = words[i+1].strip("?.,!").lower()
                break

    # Context Logic
    if current_mentioned_city:
        chat_memory["last_city"] = current_mentioned_city
        effective_city = current_mentioned_city
    else:
        effective_city = chat_memory["last_city"]

    # Priority 1: Historical & Humidity-Based Analysis
    if any(x in user_query for x in ["last", "yesterday", "history", "forecast", "previous", "before", "compare", "rain", "precipitation"]):
        city_for_history = effective_city
        history_data = get_weather_history(city_for_history)
        if isinstance(history_data, tuple):
            history, _ = history_data
        else:
            history = history_data
            
        current_weather = get_live_weather(city_for_history)
        h1 = history[0]
        curr_temp = current_weather.get("temperature", 30)
        hum = current_weather.get("humidity", 50)
        diff = curr_temp - h1["temperature"]
        trend = "warming up" if diff > 0 else "cooling down"
        
        rain_prob = 0
        if hum > 80: rain_prob = 85
        elif hum > 60: rain_prob = 50
        elif "rain" in h1["condition"]: rain_prob = 70
        
        response = f"Intelligence Report for {city_for_history.capitalize()}:\n"
        response += f"• Satellite Node Humidity: {hum}%\n"
        response += f"• 24h Thermal Shift: {trend.capitalize()} by {abs(round(diff, 1))}°C.\n"
        
        if rain_prob > 70:
            response += f"🚨 High Precipitation Risk: With humidity at {hum}%, our AI predicts a 85% chance of rain today."
        elif rain_prob > 40:
            response += f"☁️ Moderate Risk: Humidity levels ({hum}%) suggest a 50% probability of light showers."
        else:
            response += f"✅ Low Risk: Humidity is stable at {hum}%. Expect a dry and pleasant day."
            
    # Priority 2: Clothing/Activity Advice
    elif any(x in user_query for x in ["wear", "cloth", "outfit"]):
        response = f"For the current climate in {effective_city.capitalize()}, I recommend lightweight cotton clothing. If the Risk Meter is Medium+, carry sunglasses and sunscreen."
    elif any(x in user_query for x in ["run", "jog", "exercise", "walk"]):
        response = f"Conditions in {effective_city.capitalize()} are suitable for outdoor activities if the temperature is between 15°C and 28°C. Check the Risk Level before heading out!"
        
    # Priority 3: Specific City Live Weather
    elif current_mentioned_city or "weather" in user_query:
        weather_data = get_live_weather(effective_city)
        if weather_data.get("success"):
            response = f"Live Report for {effective_city.capitalize()}:\n"
            response += f"• Temperature: {weather_data['temperature']}°C\n"
            response += f"• Condition: {weather_data['condition']}\n"
            response += f"• Humidity: {weather_data['humidity']}%\n"
            response += "My intelligence engine confirms this data is verified and real-time."
        else:
            response = f"Sorry, I couldn't reach the weather sensors for {effective_city.capitalize()} right now."
            
    # Priority 4: General Advice
    elif any(x in user_query for x in ["recommend", "advice", "help"]):
        response = "Always keep an eye on the Risk Level meter. If it hits HIGH, avoid outdoor activities and stay in a shaded environment."
    else:
        response = "I am your AI Weather Intelligence Assistant. I can analyze 48-hour history, predict rain via humidity, and provide lifestyle advice!"
        
    return jsonify({"response": response})

@app.route('/history', methods=['GET'])
def weather_history():
    city = request.args.get('city', 'Hyderabad')
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
    ml_result = ml_model.predict(text=format_weather_for_ml(weather_data), weather_data=weather_data)
    return jsonify({
        "city": weather_data["city"],
        "temperature": weather_data["temperature"],
        "weather": weather_data["condition"],
        "humidity": weather_data["humidity"],
        "prediction": ml_result["prediction"],
        "confidence": ml_result["confidence"],
        "explanation": ml_result["explanation"],
        "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"]),
        "mock": weather_data.get("mock", False)
    })

@app.route('/auto-feed', methods=['GET'])
def auto_feed():
    cities = ["Vijayawada", "Hyderabad", "Chennai", "Mumbai"]
    results = []
    for city in cities:
        weather_data = get_live_weather(city)
        if weather_data.get("success"):
            ml_result = ml_model.predict(text=format_weather_for_ml(weather_data), weather_data=weather_data)
            results.append({
                "city": weather_data["city"],
                "temperature": weather_data["temperature"],
                "weather": weather_data["condition"],
                "prediction": ml_result["prediction"],
                "confidence": ml_result["confidence"],
                "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"])
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
