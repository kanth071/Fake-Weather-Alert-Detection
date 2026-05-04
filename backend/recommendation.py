def get_recommendation(temp, condition="", humidity=50):
    """
    Descriptive recommendation logic consistent with the preferred UI style.
    """
    condition = condition.lower()
    
    if "rain" in condition or "storm" in condition:
        return f"🌧️ {condition.capitalize()}. High precipitation risk. Carry an umbrella and stay safe."
    
    if temp >= 30:
        if "clear" in condition or "sunny" in condition:
            return f"☀️ High temperatures today. It is best to stay in shaded or cooled environments."
        return f"🌡️ Warm conditions. Ensure you have a water bottle if planning a walk."
        
    if 20 <= temp < 30:
        if "cloud" in condition or "overcast" in condition:
            return f"☁️ {condition.capitalize()}. The weather is relatively mild and good for outdoor errands."
        return f"🌤️ Pleasant weather detected. Perfect for outdoor activities and travel."

    if temp < 20:
        return f"❄️ Cold conditions detected ({temp}°C). Wear warm clothing and protect against the chill."

    return "✅ Moderate weather conditions. Dress comfortably for your daily activities."

def manual_recommendation(text, prediction):
    """
    Strict recommendation logic for MANUAL MODE.
    """
    text_lower = text.lower()
    fake_words = [
        "100%", "for sure", "guaranteed", "definitely", "entire city", "wipe out", "destroy everything"
    ]

    if any(word in text_lower for word in fake_words):
        return "⚠️ Extreme weather claim detected. Avoid trusting this alert without official confirmation."

    if prediction == "real":
        return "🌦️ Valid weather alert detected. Stay updated with official sources."

    return "⚠️ Suspicious weather information detected. Verify from trusted weather services."
