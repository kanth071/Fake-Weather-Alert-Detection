import pandas as pd
import numpy as np
import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

class WeatherMLModel:
    def __init__(self, model_path='weather_model.pkl'):
        self.model_path = model_path
        self.pipeline = None
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            max_features=8000,
            sublinear_tf=True
        )

    def train(self, data_path):
        if not os.path.exists(data_path): return
        df = pd.read_csv(data_path)
        X = df['text']; y = df['label']
        base_model = LinearSVC(dual=False, random_state=42, C=0.5, class_weight="balanced")
        calibrated_model = CalibratedClassifierCV(base_model, cv=3)
        self.pipeline = Pipeline([("tfidf", self.vectorizer), ("clf", calibrated_model)])
        self.pipeline.fit(X, y)
        with open(self.model_path, 'wb') as f: pickle.dump(self.pipeline, f)

    def load(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: self.pipeline = pickle.load(f)
            return True
        return False

    def predict(self, text, weather_data=None):
        if self.pipeline is None:
            if not self.load(): return {"error": "Model not loaded"}

        proba = self.pipeline.predict_proba([text])[0]
        prediction = self.pipeline.predict([text])[0]
        confidence = float(np.max(proba) * 100)

        # Rule-based override for high-risk fake keywords
        text_lower = text.lower()
        fake_markers = [ "100%",
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
    "worst ever recorded"]
        if any(m in text_lower for m in fake_markers):
            prediction = "fake"
            confidence = 95.0

        # Use the updated XAI logic requested by the user
        explanation = self.explain(weather_data or {}, prediction)

        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "explanation": explanation,
            "text": text
        }

    def explain(self, weather_data, prediction):
        """
        Simplified XAI logic as requested by user.
        Generates explanations based on temperature and humidity thresholds.
        """
        temp = weather_data.get('temperature', 35)
        humidity = weather_data.get('humidity', 50)
        explanations = []

        if temp >= 30:
            explanations.append(f"temperature {temp}°C indicates high thermal conditions contributing to heat-based classification")
        elif temp < 20:
            explanations.append(f"temperature {temp}°C indicates low thermal range contributing to cold weather detection")
        else:
            explanations.append(f"temperature {temp}°C indicates moderate weather conditions")

        if humidity > 70:
            explanations.append(f"humidity {humidity}% indicates high moisture content in the atmosphere")
        else:
            explanations.append(f"humidity {humidity}% indicates normal atmospheric moisture levels")

        return explanations[:2]

if __name__ == "__main__":
    model = WeatherMLModel()
    model.train("dataset/weather_data.csv")
    test_text = "Temperature is 37°C and humidity is 85%"
    print(model.predict(text=test_text, weather_data={"temperature": 37, "humidity": 85}))