# **Aurora - Cryptocurrency Trading Dashboard**

Aurora is an interactive cryptocurrency trading dashboard built with Dash and Plotly. It enables users to analyze real-time and historical cryptocurrency market data, plan trades, and customize their viewing experience.

---

## **Table of Contents**

1. [Overview](#overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Installation](#installation)
5. [Running the Application](#running-the-application)
6. [Application Layout](#application-layout)
7. [Customizations](#customizations)
8. [Screenshots](#screenshots)
9. [Credits](#credits)

---

## **Overview**

Aurora empowers traders to **plan wisely** and **trade boldly** by providing a customizable platform to:

- Monitor real-time cryptocurrency prices.
- Visualize historical trends through dynamic charts.
- Integrate indicators like SMA (Simple Moving Average) and RSI (Relative Strength Index).
- Analyze market sentiment with an interactive heatmap.

The dashboard uses API data from **CoinGecko**, **CryptoCompare**, and **Kraken** for price updates and historical data.

---

## **Features**

- **Real-Time Prices**: Fetches up-to-date cryptocurrency prices.
- **Multiple Timeframes**: Supports `5-min`, `15-min`, `Hourly`, and `Daily` intervals.
- **Customizable Charts**: Toggle between Candlestick, Line, and Indicators (SMA/RSI/Volume).
- **Market Sentiment Heatmap**: Displays price change sentiment dynamically.
- **Coin Selection**: Supports major cryptocurrencies (XRP, BTC, ETH, SOL, etc.).
- **Optimized Caching**: Reduces API calls with intelligent data caching.
- **Interactive UI**: Smooth transitions and clean design with hover effects.

---

## **Tech Stack**

- **Backend**: Python, Dash, Flask
- **Frontend**: HTML, CSS, Dash Components
- **Data Sources**: CoinGecko API, CryptoCompare API, Kraken API
- **Libraries**:
  - `Dash` for UI framework.
  - `Plotly` for dynamic charts.
  - `NumPy` for data manipulation.
  - `Requests` for API calls.
  - `ThreadPoolExecutor` for concurrent API requests.

---

## **Installation**

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Create and activate a virtual environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # For macOS/Linux
   venv\Scripts\activate     # For Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

---

## **Running the Application**

Run the Python script to launch the dashboard:

```bash
python app.py
```

## **Application Layout**

The dashboard has two main views:

### **1. Home Page**
- **Welcome Banner**: "Trade Boldly / Plan Wisely" with a search bar.
- **Search Markets**: Select a cryptocurrency to analyze.

### **2. Main Dashboard**
- **Top Bar**:
  - Coin Selector Dropdown
  - Timeframe and Chart Type Buttons
  - Real-time Price and Percentage Change
- **Main Chart**:
  - Candlestick or Line Chart with optional indicators (SMA/RSI/Volume).
- **Heatmap**:
  - Visualizes market sentiment based on price changes.

---

## **Customizations**

### **Adding Coins**
To add a new cryptocurrency:
1. Update the `COIN_CONFIG` dictionary with its data:
   ```python
   "COIN_NAME": {
       "coingecko_id": "<id>",
       "cc_symbol": "<symbol>",
       "kraken_pair": "<kraken_pair>",
       "logo": "<logo_url>"
   }
   ```
---

## **Screenshots**

### **Home Page**
![Home Page](assets/home.png)

### **Dashboard View**
![Dashboard](assets/main.png)

---

## **Credits**

- **APIs**: CoinGecko, CryptoCompare, Kraken
- **Icons**: [cryptologos.cc](https://cryptologos.cc)
- **Tools**: Dash, Plotly, Python

---

## **License**

This project is licensed under the **MIT License**.

---

