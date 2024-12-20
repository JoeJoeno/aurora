import requests
import time
from datetime import datetime, timedelta
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import numpy as np

from coin_config import COIN_CONFIG

from indicators import calc_sma, calc_ema, calc_stochastic, calc_macd, calc_rsi

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

def fetch_historical_data(coin, interval, timeframe):
    now = time.time()
    cache_key = (coin, interval, timeframe)
    if cache_key in historical_data_cache:
        cached_time, cached_data = historical_data_cache[cache_key]
        if now - cached_time < HISTORICAL_DATA_CACHE_TTL:
            return cached_data

    cc_symbol = COIN_CONFIG[coin]["cc_symbol"]
    limit = 2000  # Increased limit to ensure sufficient data
    aggregate = 1
    url = ""

    # Determine the endpoint and parameters based on interval
    try:
        if interval.endswith("min"):
            aggregate = int(interval.rstrip("min"))
            url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={cc_symbol}&tsym=USD&limit={limit}&aggregate={aggregate}"
        elif interval.endswith("hour"):
            aggregate_str = interval.rstrip("hour")
            aggregate = int(aggregate_str) if aggregate_str.isdigit() else 1
            url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={cc_symbol}&tsym=USD&limit={limit}&aggregate={aggregate}"
        elif interval in ["1day", "1week", "1month", "3month", "6month", "1year", "ALL"]:
            aggregate = 1
            url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={cc_symbol}&tsym=USD&limit={limit}&aggregate={aggregate}"
        else:
            # Default to hourly if unknown interval
            url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={cc_symbol}&tsym=USD&limit={limit}&aggregate=1"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()["Data"]["Data"]

        if not data:
            print(f"No data received for coin: {coin}, interval: {interval}, timeframe: {timeframe}")
            return [], [], [], [], [], []

        # Convert timestamps to datetime objects
        times = [datetime.utcfromtimestamp(d["time"]) for d in data]
        opens = [d["open"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]
        closes = [d["close"] for d in data]
        volumes = [d["volumefrom"] for d in data]

        # Calculate the start time based on timeframe
        end_time = times[-1]
        if timeframe == "1day":
            start_time = end_time - timedelta(days=1)
        elif timeframe == "1week":
            start_time = end_time - timedelta(weeks=1)
        elif timeframe == "1month":
            start_time = end_time - timedelta(days=30)
        elif timeframe == "3month":
            start_time = end_time - timedelta(days=90)
        elif timeframe == "6month":
            start_time = end_time - timedelta(days=180)
        elif timeframe == "1year":
            start_time = end_time - timedelta(days=365)
        elif timeframe == "YTD":
            start_time = datetime(end_time.year, 1, 1)
        elif timeframe == "5yr":
            start_time = end_time - timedelta(days=5*365)
        elif timeframe == "ALL":
            start_time = datetime(1970, 1, 1)
        else:
            start_time = end_time - timedelta(days=30)  # Default to 1 month

        # Filter the data based on start_time
        filtered_times = []
        filtered_opens = []
        filtered_highs = []
        filtered_lows = []
        filtered_closes = []
        filtered_volumes = []
        for t, o, h, l, c, v in zip(times, opens, highs, lows, closes, volumes):
            if t >= start_time:
                filtered_times.append(t)
                filtered_opens.append(o)
                filtered_highs.append(h)
                filtered_lows.append(l)
                filtered_closes.append(c)
                filtered_volumes.append(v)

        # Cache the filtered data
        historical_data_cache[cache_key] = (now, (filtered_times, filtered_opens, filtered_highs, filtered_lows, filtered_closes, filtered_volumes))
        return filtered_times, filtered_opens, filtered_highs, filtered_lows, filtered_closes, filtered_volumes
    except Exception as e:
        print(f"Error fetching historical data for {coin} with interval {interval} and timeframe {timeframe}: {e}")
        return [], [], [], [], [], []


def home_layout():
    return html.Div(
        className="home-container",
        children=[
            
            # Top Bar with Logo
            html.Div(className="home-logo-container", children=[
                html.Img(
                    src=app.get_asset_url("aurora_logo.png"),  # Use correct file path
                    className="home-logo",
                    alt="Aurora Logo"
                )
            ]),
            
            # Background Overlay & Hero Section
            html.Div(className="hero-section", children=[
                html.Div(className="hero-content", children=[
                    html.H1("Trade Boldly / Plan Wisely.", className="hero-title"),
                    html.P(
                        "Success starts with strategy, thrives on precision.",
                        className="hero-subtitle"
                    ),
                ]),
            ]),
            
            # Search Markets Section
            html.Div(className="search-container", children=[
                html.Div(className="search-box-wrapper", children=[
                    dcc.Dropdown(
                        id="search-crypto-dropdown",
                        options=get_sorted_dropdown_options(),
                        placeholder="Search market here",
                        className="search-box"
                    )
                ])
            ])

        ]
     )

def main_layout(selected_coin="BTC"):
    return html.Div([
        # Top Bar
        html.Div(className="top-bar", children=[
            # Logo Link
            dcc.Link(
                href="/",
                children=html.Img(src=AURORA_LOGO_URL, className="aurora-logo-topbar"),
            ),
            
            # Dropdown Selector for Cryptos
            html.Div(className="crypto-selector-container", children=[
                dcc.Dropdown(
                    id="crypto-selector",
                    options=get_sorted_dropdown_options(),
                    clearable=False,
                    value=selected_coin,  # Default selected
                    placeholder="Select a cryptocurrency",
                    style={"width": "180px", "color": "black"}  # Adjust dropdown width and style
                )
            ]),
            
            # Indicators Dropdown and Interval Dropdown
            html.Div(className="dropdown-container", children=[
                # Indicators Dropdown
                html.Div(className="indicators-dropdown-container", children=[
                    dcc.Dropdown(
                        id="indicators-dropdown",
                        options=[
                            {"label": "Candle", "value": "candle"},
                            {"label": "Line", "value": "line"},
                            {"label": "SMA", "value": "sma"},
                            {"label": "RSI", "value": "rsi"},
                            {"label": "Volume", "value": "volume"},
                            {"label": "MACD", "value": "macd"},
                            {"label": "Stochastic Oscillator", "value": "stochastic"},
                            {"label": "EMA", "value": "ema"},
                        ],
                        clearable=False,
                        value=["candle"],  # Default selection
                        multi=True,
                        placeholder="Select indicators",
                        style={"width": "150px", "color": "black"}
                    ),
                ]),

                # Interval Selection Dropdown
                html.Div(className="interval-dropdown-container", children=[
                    dcc.Dropdown(
                        id="interval-dropdown",
                        options=[
                            {"label": "1 Minute", "value": "1min"},
                            {"label": "5 Minutes", "value": "5min"},
                            {"label": "15 Minutes", "value": "15min"},
                            {"label": "30 Minutes", "value": "30min"},
                            {"label": "1 Hour", "value": "1hour"},
                            {"label": "5 Hours", "value": "5hour"},
                            {"label": "1 Day", "value": "1day"},
                            {"label": "1 Week", "value": "1week"},
                            {"label": "1 Month", "value": "1month"},
                        ],
                        value="1hour",  # Default value
                        clearable=False,
                        style={"width": "120px", "color": "black"}
                    ),
                ]),
            ]),

            # Timeframe Duration Buttons
            html.Div(className="timeframe-buttons", children=[
                html.Button("1D", id="btn-1day", className="timeframe-button"),
                html.Button("1W", id="btn-1week", className="timeframe-button"),
                html.Button("1M", id="btn-1month", className="timeframe-button"),
                html.Button("3M", id="btn-3month", className="timeframe-button"),
                html.Button("6M", id="btn-6month", className="timeframe-button"),
                html.Button("1Y", id="btn-1year", className="timeframe-button"),
                html.Button("YTD", id="btn-YTD", className="timeframe-button"),
                html.Button("5Y", id="btn-5yr", className="timeframe-button"),
                html.Button("All", id="btn-ALL", className="timeframe-button"),
            ]),

            # Price Info
            html.Div(className="price-info", children=[
                html.Img(id="selected-coin-price-logo", className="selected-coin-price-logo"),
                html.Span(id="current-price"),
                html.Span(id="price-change")
            ])
        ]),

        # Main Content
        html.Div(className="main-content", children=[
            # Graph Container with Candlestick Chart
            html.Div(className="graph-container", children=[
                dcc.Graph(id="candlestick-chart", style={"height": "800px","marginLeft": "60px"}),
            ]),
        ]),
        
        html.Div(className="contact-section", children=[
            html.H2("Contact Me", className="contact-title"),
            html.P("Feel free to reach out for any inquiries, feedback, or collaboration opportunities.", className="contact-description"),
            html.Div(className="contact-details", children=[
                html.P([
                    "Email: ",
                    html.A("rhettadambusiness@example.com", href="mailto:rhettadambusiness@example.com", className="contact-link")
                ]),
                html.P([
                    "GitHub: ",
                    html.A("Github.com", href="https://github.com/rhettadam", target="_blank", className="contact-link")
                           ]),
                html.P([
                    "LinkedIn: ",
                    html.A("linkedin.com/in/rhettadam", href="https://linkedin.com/in/rhettadam", target="_blank", className="contact-link")
                    ]),
                ]),
        ], style={"marginTop": "20px", "padding": "20px", "backgroundColor": "#1e1e2f", "color": "white"}),


        # Hidden Components
        dcc.Interval(
            id="update-interval",
            interval=15*1000,  # Update every 15 seconds
            n_intervals=0
        ),

        dcc.Store(id='last-price-store', data=None),
        dcc.Store(id='toggles-store', data={
            "coin": selected_coin,
            "interval": "1hour",
            "timeframe": "1week",
            "chart_type": "candle",
            "sma_on": False,
            "rsi_on": False,
            "volume_on": False,
            "macd_on": False,
            "stochastic_on": False,
            "ema_on": False,
        })
    ], className="main-layout")

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),  # URL routing
    dcc.Store(id="selected-coin-store", data=None),  # Store for selected coin
    html.Div(id="page-content")  # Dynamic content area
])

# Render correct page based on URL
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    State("selected-coin-store", "data")
)
def display_page(pathname, selected_coin):
    if pathname == "/":
        return home_layout()
    elif pathname == "/main":
        return main_layout(selected_coin or "BTC")
    else:
        return html.H1("404: Page not found", style={"textAlign": "center", "color": "red"})

# Navigate to Main Layout and store selected crypto
@app.callback(
    [Output("url", "pathname"), Output("selected-coin-store", "data")],
    Input("search-crypto-dropdown", "value"),
    prevent_initial_call=True
)
def navigate_to_main_page(crypto_selected):
    if crypto_selected:
        return "/main", crypto_selected
    return "/", None

@app.callback(
    Output('toggles-store', 'data'),
    [
        Input('crypto-selector', 'value'),
        Input('interval-dropdown', 'value'),
        Input('indicators-dropdown', 'value'),# New Input for Interval Dropdown
        Input('btn-1day', 'n_clicks'),
        Input('btn-1week', 'n_clicks'),
        Input('btn-1month', 'n_clicks'),
        Input('btn-3month', 'n_clicks'),
        Input('btn-6month', 'n_clicks'),
        Input('btn-1year', 'n_clicks'),
        Input('btn-YTD', 'n_clicks'),
        Input('btn-5yr', 'n_clicks'),
        Input('btn-ALL', 'n_clicks'),
    ],
    [State('toggles-store', 'data')],
    prevent_initial_call=True
)
def update_toggles(selected_coin,
                   interval_value,
                   indicators_selected,
                   b1day, b1week, b1month, b3month, b6month, b1year, bYTD, b5yr, bALL,
                   toggles):
    ctx = dash.callback_context

    if not ctx.triggered:
        return toggles
    changed_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Update coin selection
    if changed_id == 'crypto-selector' and selected_coin:
        toggles["coin"] = selected_coin

    # Update interval selection from dropdown
    elif changed_id == 'interval-dropdown' and interval_value:
        toggles["interval"] = interval_value

    # Update indicators from Indicators Dropdown
    elif changed_id == 'indicators-dropdown':
        # Handle Chart Type
        if "candle" in indicators_selected:
            toggles["chart_type"] = "candle"
            # Ensure only 'candle' or 'line' is selected
            if "line" in indicators_selected:
                indicators_selected.remove("line")
        elif "line" in indicators_selected:
            toggles["chart_type"] = "line"
            if "candle" in indicators_selected:
                indicators_selected.remove("candle")
        else:
            # Default chart type if neither is selected
            toggles["chart_type"] = "candle"

        # Handle Indicators
        toggles["sma_on"] = "sma" in indicators_selected
        toggles["rsi_on"] = "rsi" in indicators_selected
        toggles["volume_on"] = "volume" in indicators_selected
        toggles["macd_on"] = "macd" in indicators_selected
        toggles["stochastic_on"] = "stochastic" in indicators_selected
        toggles["ema_on"] = "ema" in indicators_selected

    # Update timeframe selection from buttons
    elif changed_id in ['btn-1day', 'btn-1week', 'btn-1month', 'btn-3month', 'btn-6month', 'btn-1year', 'btn-YTD', 'btn-5yr', 'btn-ALL']:
        timeframe_map = {
            'btn-1day': "1day",
            'btn-1week': "1week",
            'btn-1month': "1month",
            'btn-3month': "3month",
            'btn-6month': "6month",
            'btn-1year': "1year",
            'btn-YTD': "YTD",
            'btn-5yr': "5yr",
            'btn-ALL': "ALL",
        }
        set_timeframe = timeframe_map.get(changed_id, "1month")
        toggles["timeframe"] = set_timeframe

    return toggles

@app.callback(
    [
        Output("selected-coin-price-logo", "src"),
        Output("current-price", "children"),
        Output("price-change", "children"),
        Output("price-change", "className"),
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
    coin = toggles.get("coin", "BTC")
    interval = toggles.get("interval", "1hour")
    timeframe = toggles.get("timeframe", "1month")
    chart_type = toggles.get("chart_type", "candle")
    sma_on = toggles.get("sma_on", False)
    rsi_on = toggles.get("rsi_on", False)
    volume_on = toggles.get("volume_on", False)
    macd_on = toggles.get("macd_on", False)
    stochastic_on = toggles.get("stochastic_on", False)
    ema_on = toggles.get("ema_on", False)

    price, coingecko_data = fetch_current_price_and_data(coin)
    times, opens, highs, lows, closes, volumes = fetch_historical_data(coin, interval, timeframe)

    if not times:
        # If no data is returned, avoid plotting
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#121212",
            plot_bgcolor="#220d2b",
            font=dict(color='white')
        )
        price_text = "..."
        change_text = "0.00%"
        change_class = "percentage-white"
        current_price_store = last_price
    else:
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

        closes_array = np.array(closes, dtype=float)

        # SMA if on
        if sma_on:
            sma_values = calc_sma(closes_array)
            fig.add_trace(go.Scatter(
                x=times, y=sma_values, mode='lines', line=dict(color='yellow', width=2),
                name="SMA(14)"
            ))

        # RSI if on
        if rsi_on:
            rsi_values = calc_rsi(closes_array, period=7)
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
                    range=[0, 100],
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

        # MACD if on
        if macd_on:
            macd, signal = calc_macd(closes_array)
            fig.add_trace(go.Scatter(
                x=times, y=macd, mode='lines', line=dict(color='cyan', width=1),
                name="MACD",
                yaxis="y4"
            ))
            fig.add_trace(go.Scatter(
                x=times, y=signal, mode='lines', line=dict(color='red', width=1),
                name="Signal Line",
                yaxis="y4"
            ))
            fig.update_layout(
                yaxis4=dict(
                    overlaying='y',
                    side='right',
                    position=0.95,
                    range=[min(macd), max(macd)],
                    showgrid=False,
                    tickfont=dict(color='cyan'),
                    title='MACD'
                )
            )

        # Stochastic Oscillator if on
        if stochastic_on:
            stochastic_k, stochastic_d = calc_stochastic(closes_array)
            fig.add_trace(go.Scatter(
                x=times, y=stochastic_k, mode='lines', line=dict(color='green', width=1),
                name='Stochastic %K',
                yaxis='y5'
            ))
            fig.add_trace(go.Scatter(
                x=times, y=stochastic_d, mode='lines', line=dict(color='blue', width=1),
                name='Stochastic %D',
                yaxis='y5'
            ))
            fig.update_layout(
                yaxis5=dict(
                    overlaying='y',
                    side='right',
                    position=0.98,
                    range=[0, 100],
                    showgrid=False,
                    tickfont=dict(color='green'),
                    title='Stochastic Oscillator'
                )
            )

        # EMA if on
        if ema_on:
            ema_values = calc_ema(closes_array, period=20)
            fig.add_trace(go.Scatter(
                x=times, y=ema_values, mode='lines', line=dict(color='lime', width=1),
                name='EMA(20)'
            ))

        fig.update_layout(
            paper_bgcolor="#121212",
            plot_bgcolor="#1e1e2f",
            xaxis=dict(
                gridcolor="gray",
                showgrid=True,
                showline=False,
                linecolor='white',
                tickfont=dict(color='white'),
            ),
            yaxis=dict(
                gridcolor="gray",
                showgrid=True,
                showline=False,
                linecolor='white',
                tickfont=dict(color='white'),
            ),
            font=dict(color='white'),
            margin=dict(l=50, r=150, t=50, b=50)  # Increased right margin to accommodate additional y-axes
        )

        # Selected coin logo next to the price:
        selected_coin_logo_src = COIN_CONFIG[coin]["logo"]

    return (
        selected_coin_logo_src,
        price_text,
        change_text,
        change_class,
        fig,
        current_price_store
    )

@app.callback(
    [
        Output("btn-1day", "className"),
        Output("btn-1week", "className"),
        Output("btn-1month", "className"),
        Output("btn-3month", "className"),
        Output("btn-6month", "className"),
        Output("btn-1year", "className"),
        Output("btn-YTD", "className"),
        Output("btn-5yr", "className"),
        Output("btn-ALL", "className"),
    ],
    Input("toggles-store", "data")
)
def update_timeframe_button_styles(toggles):
    timeframe = toggles.get("timeframe", "1month")
    return [
        "timeframe-button selected" if timeframe == "1day" else "timeframe-button",
        "timeframe-button selected" if timeframe == "1week" else "timeframe-button",
        "timeframe-button selected" if timeframe == "1month" else "timeframe-button",
        "timeframe-button selected" if timeframe == "3month" else "timeframe-button",
        "timeframe-button selected" if timeframe == "6month" else "timeframe-button",
        "timeframe-button selected" if timeframe == "1year" else "timeframe-button",
        "timeframe-button selected" if timeframe == "YTD" else "timeframe-button",
        "timeframe-button selected" if timeframe == "5yr" else "timeframe-button",
        "timeframe-button selected" if timeframe == "ALL" else "timeframe-button",
    ]

def get_sorted_dropdown_options():
    # Group coins by category
    categories = {}
    for coin, details in COIN_CONFIG.items():
        category = details.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "label": f"{coin} ({details['coingecko_id'].title()})",
            "value": coin
        })
    
    # Sort categories alphabetically
    sorted_categories = sorted(categories.items())

    # Format dropdown options with headers
    dropdown_options = []
    for category, coins in sorted_categories:
        # Add a category header (disabled option)
        dropdown_options.append({"label": f"--- {category} ---", "value": None, "disabled": True})
        # Add coins under this category
        dropdown_options.extend(sorted(coins, key=lambda x: x["label"]))
    
    return dropdown_options


if __name__ == "__main__":
    app.run_server(debug=False)
