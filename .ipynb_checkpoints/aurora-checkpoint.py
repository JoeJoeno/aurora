import requests
import time
from datetime import datetime
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import numpy as np

COIN_CONFIG = {
    "XRP": {
        "coingecko_id": "ripple",
        "cc_symbol": "XRP",
        "kraken_pair": "XRPUSD",
        "logo": "https://cryptologos.cc/logos/xrp-xrp-logo.svg?v=023"
    },
    "BTC": {
        "coingecko_id": "bitcoin",
        "cc_symbol": "BTC",
        "kraken_pair": "XXBTZUSD",
        "logo": "https://cryptologos.cc/logos/bitcoin-btc-logo.svg?v=023"
    },
    "ETH": {
        "coingecko_id": "ethereum",
        "cc_symbol": "ETH",
        "kraken_pair": "XETHZUSD",
        "logo": "https://cryptologos.cc/logos/ethereum-eth-logo.svg?v=023"
    }
}

PRICE_CACHE_TTL = 1
HISTORICAL_DATA_CACHE_TTL = 300
COINGECKO_CACHE_TTL = 60

price_cache = {}
historical_data_cache = {}
coingecko_extra_cache = {}

app = dash.Dash(__name__)
server = app.server
app.title = "Aurora"

AURORA_LOGO_URL = app.get_asset_url('aurora_logo.png')

from concurrent.futures import ThreadPoolExecutor

def fetch_current_price_and_data(coin):
    now = time.time()
    
    # Check cache first
    if coin in price_cache and coin in coingecko_extra_cache:
        cached_time_price, cached_price = price_cache[coin]
        cached_time_data, cached_data = coingecko_extra_cache[coin]
        if now - cached_time_price < PRICE_CACHE_TTL and now - cached_time_data < COINGECKO_CACHE_TTL:
            return cached_price, cached_data

    # Get coin-specific configuration
    conf = COIN_CONFIG[coin]
    coingecko_url = (f"https://api.coingecko.com/api/v3/simple/price"
                     f"?ids={conf['coingecko_id']}&vs_currencies=usd"
                     f"&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true")
    cryptocompare_url = f"https://min-api.cryptocompare.com/data/price?fsym={conf['cc_symbol']}&tsyms=USD"
    kraken_url = f"https://api.kraken.com/0/public/Ticker?pair={conf['kraken_pair']}" if conf['kraken_pair'] else None

    # List of URLs to fetch
    urls = [coingecko_url, cryptocompare_url]
    if kraken_url:
        urls.append(kraken_url)

    # Fetch data concurrently
    def fetch_url(url):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return url, response.json()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return url, None

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_url, urls))

    # Parse results
    prices = []
    coingecko_data = None

    for url, data in results:
        if not data:
            continue
        if "coingecko" in url:
            coingecko_data = data.get(conf['coingecko_id'], {})
            if 'usd' in coingecko_data:
                prices.append(coingecko_data['usd'])
        elif "cryptocompare" in url:
            prices.append(data.get('USD'))
        elif "kraken" in url and data.get('result'):
            pair = list(data['result'].keys())[0]
            prices.append(float(data['result'][pair]['c'][0]))

    # Calculate average price
    if prices:
        avg_price = sum(prices) / len(prices)
        price_cache[coin] = (time.time(), avg_price)
        if coingecko_data:
            coingecko_extra_cache[coin] = (time.time(), coingecko_data)
        return avg_price, coingecko_data
    else:
        return None, None

def fetch_historical_data(coin, interval):
    now = time.time()
    cache_key = (coin, interval)
    if cache_key in historical_data_cache:
        cached_time, cached_data = historical_data_cache[cache_key]
        if now - cached_time < HISTORICAL_DATA_CACHE_TTL:
            return cached_data

    cc_symbol = COIN_CONFIG[coin]["cc_symbol"]

    if interval == "5min":
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={cc_symbol}&tsym=USD&limit=50&aggregate=5"
    elif interval == "15min":
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={cc_symbol}&tsym=USD&limit=50&aggregate=15"
    elif interval == "hourly":
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={cc_symbol}&tsym=USD&limit=50"
    elif interval == "daily":
        url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={cc_symbol}&tsym=USD&limit=30"
    else:
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={cc_symbol}&tsym=USD&limit=50"

    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()["Data"]["Data"]

    times = [datetime.utcfromtimestamp(d["time"]) for d in data]
    opens = [d["open"] for d in data]
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]
    closes = [d["close"] for d in data]
    volumes = [d["volumefrom"] for d in data]

    historical_data_cache[cache_key] = (now, (times, opens, highs, lows, closes, volumes))
    return times, opens, highs, lows, closes, volumes

def calc_sma(values, period=14):
    sma = []
    for i in range(len(values)):
        if i < period-1:
            sma.append(None)
        else:
            sma.append(np.mean(values[i-period+1:i+1]))
    return sma

def calc_rsi(values, period=14):
    if len(values) < period:
        return [None]*len(values)
    changes = np.diff(values)
    gains = np.where(changes > 0, changes, 0)
    losses = np.where(changes < 0, -changes, 0)

    rsi = [None]*(period)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain/avg_loss
        rsi.append(100 - (100/(1+rs)))

    for i in range(period+1, len(values)):
        gain = gains[i-1]
        loss = losses[i-1]
        avg_gain = (avg_gain*(period-1) + gain)/period
        avg_loss = (avg_loss*(period-1) + loss)/period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain/avg_loss
            rsi.append(100 - (100/(1+rs)))
    return [None]*period + rsi

def loading_screen_layout():
    return html.Div(
        className="loading-screen",
        children=[
            html.Div(
                className="loading-container",
                children=[
                    html.Img(src=AURORA_LOGO_URL, className="aurora-logo-loading"),
                    html.Div(className="spinner"),
                    html.P("Loading assets", style={
                        "color":"white",
                        "marginTop":"10px",
                        "fontSize":"18px"
                    })
                ]
            )
        ]
    )

def main_layout():
    return html.Div([
        html.Div(className="top-bar", children=[
            html.Img(src=AURORA_LOGO_URL, className="aurora-logo-topbar"),
            html.Div(className="coins-container", children=[
                html.Img(src=COIN_CONFIG["XRP"]["logo"], id="xrp-logo", className="coin-logo"),
                html.Img(src=COIN_CONFIG["BTC"]["logo"], id="btc-logo", className="coin-logo"),
                html.Img(src=COIN_CONFIG["ETH"]["logo"], id="eth-logo", className="coin-logo"),
            ]),
            
            html.Div(className="dropdown-container", children=[
                html.Button("5-min", id="btn-5min", className="timeframe-button"),
                html.Button("15-min", id="btn-15min", className="timeframe-button"),
                html.Button("Hourly", id="btn-hourly", className="timeframe-button"),
                html.Button("Daily", id="btn-daily", className="timeframe-button"),
                html.Button("Candle", id="btn-candle", className="charttype-button"),
                html.Button("Line", id="btn-line", className="charttype-button"),
                html.Button("SMA", id="btn-sma", className="indicator-button"),
                html.Button("RSI", id="btn-rsi", className="indicator-button"),
                html.Button("Volume", id="btn-volume", className="indicator-button"),
            ]),
            
            # We'll show selected coin logo next to the price
            html.Div(className="price-info", children=[
                html.Img(id="selected-coin-price-logo", className="selected-coin-price-logo"),
                html.Span(id="current-price"),
                html.Span(id="price-change")
            ])
        ]),

        dcc.Graph(id="candlestick-chart", style={"height": "600px"}),

        html.Div(className="info-panel", children=[
            html.Span(id="market-cap"),
            html.Span(id="volume")
        ]),

        dcc.Interval(
            id="update-interval",
            interval=15*1000,
            n_intervals=0
        ),

        dcc.Store(id='last-price-store', data=None),
        dcc.Store(id='selected-coin', data='XRP'),
        dcc.Store(id='toggles-store', data={
            "coin": "XRP",
            "timeframe": "hourly",
            "chart_type": "candle",
            "sma_on": False,
            "rsi_on": False,
            "volume_on": False
        })
    ], className="main-layout")

app.layout = html.Div([
    dcc.Store(id="page-state", data="loading"),
    html.Div(id="page-content"),
    dcc.Interval(id="loading-interval", interval=2000, n_intervals=0, max_intervals=1)
])

@app.callback(
    Output("page-content", "children"),
    Input("page-state", "data")
)
def render_page(page):
    if page == "loading":
        return loading_screen_layout()
    else:
        return main_layout()

@app.callback(
    Output("page-state", "data"),
    Input("loading-interval", "n_intervals"),
    State("page-state", "data")
)
def load_data(n, current_state):
    if current_state == "loading" and n == 1:
        return "main"
    return current_state

@app.callback(
    Output('toggles-store', 'data'),
    [
        Input('xrp-logo', 'n_clicks'),
        Input('btc-logo', 'n_clicks'),
        Input('eth-logo', 'n_clicks'),
        Input('btn-5min', 'n_clicks'),
        Input('btn-15min', 'n_clicks'),
        Input('btn-hourly', 'n_clicks'),
        Input('btn-daily', 'n_clicks'),
        Input('btn-candle', 'n_clicks'),
        Input('btn-line', 'n_clicks'),
        Input('btn-sma', 'n_clicks'),
        Input('btn-rsi', 'n_clicks'),
        Input('btn-volume', 'n_clicks'),
    ],
    State('toggles-store', 'data')
)
def update_toggles(xrp_click, btc_click, eth_click,
                   b5, b15, bhourly, bdaily,
                   bcandle, bline,
                   bsma, brsi, bvolume,
                   toggles):
    ctx = dash.callback_context
    if not ctx.triggered:
        return toggles
    changed_id = ctx.triggered[0]['prop_id'].split('.')[0]

    def toggle_bool(key):
        toggles[key] = not toggles[key]

    if changed_id == 'xrp-logo':
        toggles["coin"] = "XRP"
    elif changed_id == 'btc-logo':
        toggles["coin"] = "BTC"
    elif changed_id == 'eth-logo':
        toggles["coin"] = "ETH"

    elif changed_id == 'btn-5min':
        toggles["timeframe"] = "5min"
    elif changed_id == 'btn-15min':
        toggles["timeframe"] = "15min"
    elif changed_id == 'btn-hourly':
        toggles["timeframe"] = "hourly"
    elif changed_id == 'btn-daily':
        toggles["timeframe"] = "daily"

    elif changed_id == 'btn-candle':
        toggles["chart_type"] = "candle"
    elif changed_id == 'btn-line':
        toggles["chart_type"] = "line"

    elif changed_id == 'btn-sma':
        toggle_bool("sma_on")
    elif changed_id == 'btn-rsi':
        toggle_bool("rsi_on")
    elif changed_id == 'btn-volume':
        toggle_bool("volume_on")

    return toggles

@app.callback(
    [
     Output("selected-coin-price-logo", "src"),
     Output("current-price", "children"),
     Output("price-change", "children"),
     Output("price-change", "className"),
     Output("market-cap", "children"),
     Output("market-cap", "className"),
     Output("volume", "children"),
     Output("volume", "className"),
     Output("candlestick-chart", "figure"),
     Output('last-price-store', 'data')
    ],
    [
     Input("toggles-store", "data"),
     Input("update-interval", "n_intervals")
    ],
    [State('last-price-store', 'data')]
)
def update_chart(toggles, n_intervals, last_price):
    coin = toggles["coin"]
    timeframe = toggles["timeframe"]
    chart_type = toggles["chart_type"]
    sma_on = toggles["sma_on"]
    rsi_on = toggles["rsi_on"]
    volume_on = toggles["volume_on"]

    price, coingecko_data = fetch_current_price_and_data(coin)
    times, opens, highs, lows, closes, volumes = fetch_historical_data(coin, timeframe)


    market_cap_text = "MC: ..."
    mc_class = "percentage-white"
    volume_text = "Vol: ..."
    vol_class = "percentage-white"
    
    if coingecko_data:
        mc = coingecko_data.get('usd_market_cap')
        vol = coingecko_data.get('usd_24h_vol')
        if mc is not None:
            market_cap_text = f"MC: ${mc:,.0f}"
        if vol is not None:
            volume_text = f"Vol: ${vol:,.0f}"

    if price is None:
        price_text = "..."
        current_price_store = last_price
        hist_change = 0.0
    else:
        price_text = f"${price:.4f}"
        current_price_store = price
        if len(closes) > 1:
            start_price = closes[0]
            end_price = closes[-1]
            hist_change = ((end_price - start_price)/start_price)*100
        else:
            hist_change = 0.0

    if hist_change > 0:
        change_text = f"+{hist_change:.2f}%"
        change_class = "percentage-green"
    elif hist_change < 0:
        change_text = f"{hist_change:.2f}%"
        change_class = "percentage-red"
    else:
        change_text = f"{hist_change:.2f}%"
        change_class = "percentage-white"

    fig = go.Figure()

    if chart_type == "candle":
        fig.add_trace(go.Candlestick(
            x=times,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            increasing_line_color="green",
            decreasing_line_color="red",
            name=coin
        ))
    else:
        fig.add_trace(go.Scatter(
            x=times, y=closes, mode='lines', line=dict(color='#ff8aff', width=2),
            name=coin
        ))

    closes_array = np.array(closes,dtype=float)

    # SMA if on
    if sma_on:
        sma_values = calc_sma(closes_array)
        fig.add_trace(go.Scatter(
            x=times, y=sma_values, mode='lines', line=dict(color='yellow', width=2),
            name="SMA(14)"
        ))

    # RSI if on
    if rsi_on:
        rsi_values = calc_rsi(closes_array)
        fig.add_trace(go.Scatter(
            x=times, y=rsi_values, mode='lines', line=dict(color='magenta', width=2),
            name="RSI(14)",
            yaxis="y2"
        ))
        fig.update_layout(
            yaxis2=dict(
                overlaying='y',
                side='right',
                position=0.99,
                range=[0,100],
                showgrid=False,
                tickfont=dict(color='magenta'),
                title='RSI'
            )
        )

    # Volume if on
    if volume_on:
        fig.add_trace(go.Bar(
            x=times, y=volumes, name='Volume',
            marker_color='rgba(200,200,200,0.3)',
            yaxis='y3'
        ))
        fig.update_layout(
            yaxis3=dict(
                overlaying='y',
                side='right',
                showgrid=False,
                tickfont=dict(color='rgba(200,200,200,0.7)'),
                title='Volume'
            )
        )

    fig.update_layout(
        paper_bgcolor="#121212",
        plot_bgcolor="#1e1e2f",
        xaxis=dict(
            gridcolor="gray",
            showgrid=True,
            showline=True,
            linecolor='white',
            tickfont=dict(color='white'),
            title='Time',
            titlefont=dict(color='white')
        ),
        yaxis=dict(
            gridcolor="gray",
            showgrid=True,
            showline=True,
            linecolor='white',
            tickfont=dict(color='white'),
            title='Price (USD)',
            titlefont=dict(color='white')
        ),
        font=dict(color='white'),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    # selected coin logo next to the price:
    selected_coin_logo_src = COIN_CONFIG[coin]["logo"]

    return (selected_coin_logo_src,
            price_text, change_text, change_class,
            market_cap_text, "percentage-white",
            volume_text, "percentage-white",
            fig, current_price_store)

@app.callback(
    [
        Output("btn-5min", "className"),
        Output("btn-15min", "className"),
        Output("btn-hourly", "className"),
        Output("btn-daily", "className"),
    ],
    Input("toggles-store", "data")
)
def update_timeframe_styles(toggles):
    timeframe = toggles["timeframe"]
    return [
        "timeframe-button selected" if timeframe == "5min" else "timeframe-button",
        "timeframe-button selected" if timeframe == "15min" else "timeframe-button",
        "timeframe-button selected" if timeframe == "hourly" else "timeframe-button",
        "timeframe-button selected" if timeframe == "daily" else "timeframe-button",
    ]

@app.callback(
    [
        Output("btn-candle", "className"),
        Output("btn-line", "className"),
        Output("btn-sma", "className"),
        Output("btn-rsi", "className"),
        Output("btn-volume", "className"),
    ],
    Input("toggles-store", "data")
)
def update_tool_styles(toggles):
    return [
        "charttype-button selected" if toggles["chart_type"] == "candle" else "charttype-button",
        "charttype-button selected" if toggles["chart_type"] == "line" else "charttype-button",
        "indicator-button selected" if toggles["sma_on"] else "indicator-button",
        "indicator-button selected" if toggles["rsi_on"] else "indicator-button",
        "indicator-button selected" if toggles["volume_on"] else "indicator-button",
    ]

if __name__ == "__main__":
    app.run_server(debug=False)
