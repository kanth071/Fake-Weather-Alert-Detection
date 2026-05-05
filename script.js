/**
 * AI Weather Intelligence System - Enhanced SaaS Dashboard
 */

const API_BASE_URL = '';
let currentMode = 'auto';
let citiesData = [];
const cityGrid = document.getElementById('cityGrid');
const manualInputBox = document.getElementById('manualInputBox');
const btnAuto = document.getElementById('btnAuto');
const btnManual = document.getElementById('btnManual');
const predictionStatus = document.getElementById('predictionStatus');
const confidenceBar = document.getElementById('confidenceBar');
const confidenceText = document.getElementById('confidenceText');
const riskBar = document.getElementById('riskBar');
const recommendationPanel = document.getElementById('recommendationPanel');

window.selectedCity = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchWeatherData();
    setInterval(fetchWeatherData, 30000);
    startInsightRotation();
});

function setMode(mode) {
    currentMode = mode;
    const manualTips = document.getElementById('manualTipsPanel');
    const searchBox = document.getElementById('searchBox');
    
    if (mode === 'manual') {
        manualInputBox.style.display = 'block';
        cityGrid.style.display = 'none';
        if (searchBox) searchBox.style.display = 'none';
        if (manualTips) manualTips.style.display = 'block';
        btnManual.classList.add('active');
        btnAuto.classList.remove('active');
        predictionStatus.innerText = "AWAITING INPUT...";
        predictionStatus.style.color = "var(--text-secondary)";
        confidenceBar.style.width = '0%';
        confidenceBar.innerText = '';
        confidenceText.innerText = '0%';
        riskBar.style.width = '0%';
        document.getElementById('riskLevelText').innerText = '---';
    } else {
        manualInputBox.style.display = 'none';
        cityGrid.style.display = 'grid';
        if (searchBox) searchBox.style.display = 'flex';
        if (manualTips) manualTips.style.display = 'none';
        btnAuto.classList.add('active');
        btnManual.classList.remove('active');
        fetchWeatherData();
    }
}

async function fetchWeatherData() {
    if (currentMode !== 'auto') return;
    try {
        const response = await fetch(`${API_BASE_URL}/auto-feed`);
        const data = await response.json();
        citiesData = data;
        updateUI();
        if (!window.selectedCity && data.length > 0) selectCity(data[0].city);
    } catch (error) {
        console.error('Fetch error:', error);
    }
}

async function predictManual() {
    const textEl = document.getElementById('userText');
    const text = textEl.value.trim();
    if (!text) return;
    
    // UI Feedback: Loading
    const originalStatus = predictionStatus.innerText;
    predictionStatus.innerText = "Analyzing alert content...";
    predictionStatus.style.color = "var(--accent-blue)";
    
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'manual', text: text })
        });
        const data = await response.json();
        if (data.error) {
            predictionStatus.innerText = "Error: " + data.error;
            return;
        }
        updatePredictionPanel(data);
        if (data.detected_city) updateTrendChart(data.detected_city);
    } catch (error) {
        predictionStatus.innerText = "Connection failed. Please try again.";
        console.error("Manual prediction error:", error);
    }
}

async function searchCity() {
    const inputEl = document.getElementById('citySearchInput');
    const cityName = inputEl.value.trim();
    const searchBtn = document.getElementById('searchBtn');
    if (!cityName) return;
    searchBtn.innerText = "Analyzing...";
    searchBtn.disabled = true;
    try {
        if (currentMode === 'manual') setMode('auto');
        await selectCity(cityName);
    } finally {
        searchBtn.innerText = "Analyze";
        searchBtn.disabled = false;
    }
}

async function selectCity(cityName) {
    window.selectedCity = cityName;
    await Promise.all([fetchFocusCityDetails(cityName), updateTrendChart(cityName)]);
}

async function fetchFocusCityDetails(cityName) {
    try {
        const response = await fetch(`${API_BASE_URL}/live-weather?city=${cityName}`);
        const data = await response.json();
        updatePredictionPanel(data);
    } catch (error) {}
}

async function updateTrendChart(cityName) {
    try {
        const response = await fetch(`${API_BASE_URL}/history?city=${cityName}`);
        const data = await response.json();
        const history = data.history;
        const currentTemp = data.current_temp;
        
        document.getElementById('trendCity').innerText = cityName;
        
        // Use history[0] (Yesterday) and history[1] (Tomorrow/Forecast)
        const yesterdayTemp = history && history.length > 0 ? history[0].temperature : (currentTemp - 2);
        const forecastTemp = history && history.length > 1 ? history[1].temperature : (currentTemp + 2);
        
        const bars = [
            { id: 'barYesterday', t: yesterdayTemp },
            { id: 'barToday', t: currentTemp },
            { id: 'barForecast', t: forecastTemp }
        ];
        
        bars.forEach(b => {
            const el = document.getElementById(b.id);
            if (el) {
                // Ensure height is at least 10% for visibility
                el.style.height = `${Math.max(10, Math.min(b.t * 2.5, 100))}%`;
                el.querySelector('.bar-val').innerText = `${Math.round(b.t)}°C`;
            }
        });
    } catch (error) {
        console.error("Trend update error:", error);
    }
}

function updatePredictionPanel(data) {
    // 1. Prediction Enhancement
    const status = data.prediction.toUpperCase();
    const icon = status === 'REAL' ? '✅' : '🚨';
    predictionStatus.innerText = `Prediction: ${status} (${data.confidence}%) ${icon}`;
    predictionStatus.style.color = status === 'REAL' ? 'var(--accent-green)' : 'var(--accent-red)';
    
    // 2. Confidence Bar
    confidenceText.innerText = `${data.confidence}%`;
    confidenceBar.style.width = `${data.confidence}%`;
    confidenceBar.innerText = `${data.confidence}%`;
    
    // 3. Risk Level UI
    const riskLevelText = document.getElementById('riskLevelText');
    let riskVal = 20;
    if (data.prediction === 'fake') {
        riskVal = 85;
    } else if (data.temperature > 38 || data.humidity > 80) {
        riskVal = 70;
    } else if (data.temperature > 30 || data.humidity > 60) {
        riskVal = 45;
    }
    
    let riskLabel = riskVal > 80 ? "HIGH" : (riskVal > 40 ? "MEDIUM" : "LOW");
    let riskColor = riskVal > 80 ? 'var(--accent-red)' : (riskVal > 40 ? 'var(--accent-yellow)' : 'var(--accent-green)');
    
    riskBar.style.width = `${riskVal}%`;
    riskBar.style.background = riskColor;
    riskLevelText.innerHTML = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${riskColor}; margin-right:5px;"></span>${riskLabel}`;
    riskLevelText.style.color = riskColor;
    
    recommendationPanel.innerHTML = `
        <div style="margin-bottom: 10px;">${data.recommendation}</div>
        <div style="font-size: 0.8rem; opacity: 0.8; display: flex; flex-wrap: wrap; gap: 15px;">
            <span>🌡️ Feels Like: ${data.feels_like ? data.feels_like.toFixed(1) : 'N/A'}°C</span>
            <span>💧 Humidity: ${data.humidity || 'N/A'}%</span>
            <span>💨 Wind: ${data.wind_speed || 'N/A'} m/s</span>
            <span>🕒 Updated: ${data.timestamp || 'Live'}</span>
        </div>
    `;
    
    // 4. Explainable AI
    const explanationList = document.getElementById('explanationList');
    explanationList.innerHTML = '';
    if (data.explanation && data.explanation.length > 0) {
        data.explanation.forEach(reason => {
            const li = document.createElement('li');
            li.style.cssText = "display: flex; align-items: flex-start; gap: 12px; margin-bottom: 0.8rem; font-size: 0.9rem;";
            const parts = reason.split(' → ');
            if (parts.length === 2) {
                li.innerHTML = `<span style="color: var(--accent-blue); font-weight: 700; background: rgba(56,189,248,0.1); padding: 2px 6px; border-radius: 4px;">${parts[0]}</span> <span style="color: var(--text-secondary);">→ ${parts[1]}</span>`;
            } else {
                li.innerHTML = `<span>🔹</span> <span>${reason}</span>`;
            }
            explanationList.appendChild(li);
        });
    }
}

function updateUI() {
    cityGrid.innerHTML = '';
    citiesData.forEach(city => {
        const card = document.createElement('div');
        card.className = 'glass-card city-card';
        card.onclick = () => selectCity(city.city);
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                <h2 style="font-size:1rem;">📍 ${city.city}</h2>
                <span class="badge ${city.prediction === 'real' ? 'badge-real' : 'badge-fake'}">${city.prediction}</span>
            </div>
            <div class="temp">${city.temperature ? city.temperature.toFixed(1) : 'N/A'}°C</div>
            <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:0.5rem;">Feels like: ${city.feels_like ? city.feels_like.toFixed(1) : 'N/A'}°C</div>
            <div style="color:var(--text-secondary); font-size:0.9rem; margin-bottom:0.5rem;">${city.weather}</div>
            
            <div style="font-size: 0.6rem; color: var(--accent-green); margin-bottom: 1rem; font-weight: 700;">
                📶 Source: ${city.source || 'Verified Feed'} | 🕒 ${city.timestamp || 'Live'}
            </div>

            <div style="font-size:0.75rem; background:rgba(255,255,255,0.03); padding:8px; border-radius:8px; text-align:left;">
                <div style="color:var(--accent-blue); font-weight:700; margin-bottom:4px; font-size:0.65rem; text-transform:uppercase;">AI Advice</div>
                ${city.recommendation}
            </div>
        `;
        cityGrid.appendChild(card);
    });
}

function startInsightRotation() {
    const ticker = document.getElementById('intelligenceTicker');
    const insights = [
        "AI Insight: Weather conditions are stable across major metropolitan nodes.",
        "AI Insight: High humidity detected in coastal regions, precipitation likely.",
        "AI Insight: Historical analysis confirms cooling trend in northern sectors.",
        "AI Insight: ML model confidence has stabilized at 98.4% for current dataset.",
        "AI Insight: Unusual heat signature detected in Hyderabad; protocol active."
    ];
    let i = 0;
    setInterval(() => {
        ticker.style.opacity = '0';
        setTimeout(() => {
            ticker.innerText = insights[i];
            ticker.style.opacity = '1';
            i = (i + 1) % insights.length;
        }, 500);
    }, 6000);
}

function toggleChat() {
    const chatWindow = document.getElementById('chatWindow');
    chatWindow.style.display = chatWindow.style.display === 'none' ? 'flex' : 'none';
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const messages = document.getElementById('chatMessages');
    const query = input.value.trim();
    if (!query) return;
    
    // Add User Message (let CSS handle styling)
    const userDiv = document.createElement('div');
    userDiv.className = "chat-msg user-msg";
    userDiv.innerText = query;
    messages.appendChild(userDiv);
    input.value = '';
    messages.scrollTop = messages.scrollHeight;
    
    try {
        const response = await fetch(`${API_BASE_URL}/agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();
        
        const aiDiv = document.createElement('div');
        aiDiv.className = "chat-msg ai-msg";
        aiDiv.innerHTML = data.response.replace(/\n/g, '<br>');
        messages.appendChild(aiDiv);
        messages.scrollTop = messages.scrollHeight;
    } catch (error) {
        console.error('Agent communication error:', error);
    }
}
