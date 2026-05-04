# 🌦️ AI Weather Intelligence & Smart Recommendation System

A production-level SaaS-style dashboard that combines real-time weather data, machine learning classification, and a smart recommendation engine.

## 🚀 Features
- **Real-time Weather**: Fetches live data from OpenWeather API.
- **ML Pipeline**: Classifies weather alerts as "Real" or "Fake" using Scikit-Learn (LinearSVC + TF-IDF).
- **Smart Recommendations**: Rule-based engine providing human-like advice (e.g., "Carry umbrella ☔").
- **Explainable AI (XAI)**: Highlights key words influencing the model's decision.
- **SaaS Dashboard**: Modern Dark UI with glassmorphism, animations, and auto-refresh.
- **Multi-City Support**: Monitors Vijayawada, Hyderabad, Chennai, and Mumbai.

## 🛠️ Tech Stack
- **Backend**: Python (Flask), Scikit-Learn, Pandas, Requests.
- **Frontend**: HTML5, Vanilla CSS, JavaScript (Fetch API).
- **Data**: Synthetic weather alert dataset for ML training.

## 📦 Folder Structure
```
weather-ai-project/
├── backend/
│   ├── app.py                  # Flask API
│   ├── weather_service.py      # API Integration
│   ├── model.py                # ML Pipeline (TF-IDF + SVC)
│   ├── recommendation.py       # Rule-based Engine
│   └── requirements.txt        # Dependencies
├── frontend/
│   ├── index.html              # Dashboard UI
│   ├── style.css               # Modern Design
│   └── script.js               # Dynamic Logic
└── dataset/
    └── weather_data.csv        # Training Data
```

## ⚙️ Setup Instructions

### 1. Backend Setup
1. Navigate to the `backend` folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Add your OpenWeather API Key in `.env`:
   ```
   OPENWEATHER_API_KEY=your_actual_key_here
   ```
   *Note: If no key is provided, the system runs in Mock Mode.*
4. Start the server:
   ```bash
   python app.py
   ```

### 2. Frontend Setup
1. Open `frontend/index.html` in any modern web browser.
2. The dashboard will automatically start fetching data from the backend.

## 🧠 ML Details
- **Model**: LinearSVC with CalibratedClassifierCV for confidence scores.
- **Vectorizer**: TF-IDF (ngram_range=(1,2)).
- **Logic**: Analyzes weather patterns and text triggers to distinguish official reports from sensationalized "fake" alerts.

---
*Developed as a Production-Level AI Project.*
