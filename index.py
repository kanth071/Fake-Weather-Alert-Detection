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
            
    # Try pattern matching: "in {City}", "at {City}", "for {City}"
    patterns = [r"in\s+([a-z]+)", r"at\s+([a-z]+)", r"for\s+([a-z]+)", r"to\s+([a-z]+)"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            potential_city = match.group(1)
            if len(potential_city) > 3: # Ignore small words like 'the', 'now'
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

@app.route('/agent', methods=['POST'])
def ai_agent():
    global chat_memory
    user_query_original = request.json.get('query', '')
    user_query = translate_to_english(user_query_original).lower()
    
    # Greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you"]
    if any(g in user_query for g in greetings):
        return jsonify({"response": "👋 Hello! I am your AI Weather Intelligence Assistant. I can analyze climate history, predict rain risks, and provide lifestyle advice for any city. How can I help you today?"})

    # City Detection
    current_mentioned_city = extract_city(user_query)
    if current_mentioned_city:
        chat_memory["last_city"] = current_mentioned_city
    
    effective_city = chat_memory["last_city"]
    weather_data = get_live_weather(effective_city)

    # Response Logic
    if any(x in user_query for x in ["last", "yesterday", "history", "forecast", "tomorrow"]):
        history_data = get_weather_history(effective_city, current_temp=weather_data.get("temperature"))
        history, _ = history_data
        
        resp = f"Intelligence Report for {effective_city.capitalize()}:\n"
        for item in history:
            resp += f"• {item['day']}: {item['temperature']}°C ({item['condition']})\n"
        
        if weather_data.get("humidity", 0) > 70:
            resp += f"\n🚨 Alert: High humidity ({weather_data['humidity']}%) detected. Rain is likely."
        else:
            resp += f"\n✅ Status: Conditions appear stable for {effective_city.capitalize()}."
        return jsonify({"response": resp})

    elif any(x in user_query for x in ["wear", "cloth", "outfit", "recommend"]):
        temp = weather_data.get("temperature", 25)
        advice = get_recommendation(temp, weather_data.get("condition", ""), weather_data.get("humidity", 50))
        return jsonify({"response": f"For {effective_city.capitalize()}, I recommend: {advice}"})

    elif "weather" in user_query or current_mentioned_city:
        if weather_data.get("success"):
            resp = f"Live Report for {effective_city.capitalize()}:\n"
            resp += f"• Temperature: {weather_data['temperature']}°C\n"
            resp += f"• Condition: {weather_data['condition'].capitalize()}\n"
            resp += f"• Humidity: {weather_data['humidity']}%\n"
            resp += f"• Source: {weather_data['source']}"
            return jsonify({"response": resp})
        else:
            return jsonify({"response": f"Sorry, I couldn't fetch data for {effective_city.capitalize()}."})

    return jsonify({"response": "I am your AI Weather Intelligence Assistant. Ask me about weather in any city, clothing advice, or 48-hour trends!"})

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
        "weather": weather_data["condition"],
        "humidity": weather_data["humidity"],
        "wind_speed": weather_data.get("wind_speed", 0),
        "prediction": ml_result["prediction"],
        "confidence": ml_result["confidence"],
        "explanation": ml_result["explanation"],
        "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"]),
        "source": weather_data["source"],
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
                "weather": weather_data["condition"],
                "prediction": ml_result["prediction"],
                "confidence": ml_result["confidence"],
                "recommendation": get_recommendation(weather_data["temperature"], weather_data["condition"], weather_data["humidity"]),
                "source": weather_data["source"]
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
