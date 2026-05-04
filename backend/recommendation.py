def get_recommendation(temp, condition="", humidity=50):
    """
    Standard recommendation logic for AUTO MODE.
    Based on temperature and humidity thresholds.
    """
    if temp >= 30:
        return "High temperature detected. Stay hydrated and avoid prolonged outdoor exposure."
    elif 20 <= temp < 30:
        return "Warm conditions detected. Carry a water bottle if planning outdoor activities."
    elif temp < 20:
        if humidity > 70:
            return "Cold and humid conditions detected. Wear warm clothing and stay dry."
        else:
            return "Cold conditions detected (below 20°C). Wear warm clothing and avoid prolonged outdoor exposure."
    return "Moderate weather conditions detected. Dress comfortably for outdoor activity."

def manual_recommendation(text, prediction):
    """
    Strict recommendation logic for MANUAL MODE.
    Focuses on alert verification and sensationalism detection.
    """
    text_lower = text.lower()
    fake_words = [
        "100%",
    "for sure",
    "guaranteed",
    "definitely",
    "entire city",
    "all areas",
    "completely destroyed",
    "wipe out",
    "destroy everything",
    "end of the city",
    "never seen before",
    "massive disaster",
    "total shutdown",
    "no chance of survival",
    "catastrophic storm",
    "apocalypse weather",
    "city will sink",
    "flood whole city",
    "level the city",
    "unlimited rainfall",
    "extreme beyond limits",
    "worst ever recorded"
    ]

    if any(word in text_lower for word in fake_words):
        return "⚠️ Extreme weather claim detected. Avoid trusting this alert without official confirmation."

    if prediction == "real":
        return "🌦️ Valid weather alert detected. Stay updated with official sources."

    return "⚠️ Suspicious weather information detected. Verify from trusted weather services."
