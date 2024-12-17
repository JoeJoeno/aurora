![Logo](assets/aurora_logo.png)

![Home Page](assets/home.png)

![Dashboard](assets/main.png)

---

## **Table of Contents**

1. [Overview](#overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Running the Application](#running-the-application)
5. [Customizations](#customizations)
6. [Credits](#credits)

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

## **Running the Application**

Run the Python script to launch the dashboard:

```bash
python app.py
```

Or you can visit the Render Development Build here:

https://aurora-vens.onrender.com/

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

## **Credits**

- **APIs**: CoinGecko, CryptoCompare, Kraken
- **Icons**: [cryptologos.cc](https://cryptologos.cc)
- **Tools**: Dash, Plotly, Python

---

## **License**

This project is licensed under the **MIT License**. See the LICENSE file for details.

Copyright (c) 2024 Rhett R. Adam

---

