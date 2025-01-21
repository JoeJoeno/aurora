import numpy as np

def calc_macd(values, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate the MACD (Moving Average Convergence Divergence) and Signal Line.
    Args:
        values (list): List of numerical values (e.g., closing prices).
        fast_period (int): Period for the fast EMA.
        slow_period (int): Period for the slow EMA.
        signal_period (int): Period for the signal line.
    Returns:
        tuple: MACD line and Signal line as lists.
    """
    # Calculate EMAs
    fast_ema = calc_ema(values, period=fast_period)
    slow_ema = calc_ema(values, period=slow_period)

    # Calculate MACD line
    macd = [f - s if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema)]

    # Calculate Signal line
    macd_no_none = [m for m in macd if m is not None]
    signal_line = [None] * (len(macd) - len(macd_no_none)) + calc_sma(macd_no_none, period=signal_period)

    return macd, signal_line


# Simple Moving Average (SMA)
def calc_sma(values, period=14):
    """
    Calculate the Simple Moving Average (SMA).
    Args:
        values (list): List of numerical values (e.g., closing prices).
        period (int): The lookback period for SMA calculation.
    Returns:
        list: SMA values with None for periods with insufficient data.
    """
    values = np.array(values, dtype=float)
    sma = np.convolve(values, np.ones(period)/period, mode='valid')
    return [None] * (period - 1) + sma.tolist()

# Relative Strength Index (RSI)
def calc_rsi(values, period=14):
    """
    Calculate the Relative Strength Index (RSI).
    Args:
        values (list): List of numerical values (e.g., closing prices).
        period (int): The lookback period for RSI calculation.
    Returns:
        list: RSI values with None for periods with insufficient data.
    """
    values = np.array(values, dtype=float)
    delta = np.diff(values, prepend=values[0])
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)

    avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return [None] * (period - 1) + rsi.tolist()

# Exponential Moving Average (EMA)
def calc_ema(values, period=20):
    """
    Calculate the Exponential Moving Average (EMA).
    Args:
        values (list): List of numerical values (e.g., closing prices).
        period (int): The lookback period for EMA calculation.
    Returns:
        list: EMA values with None for periods with insufficient data.
    """
    values = np.array(values, dtype=float)
    ema = np.zeros_like(values)
    k = 2 / (period + 1)

    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = values[i] * k + ema[i-1] * (1 - k)

    return ema.tolist()

# Bollinger Bands
def calc_bollinger_bands(values, period=20, num_std_dev=2):
    """
    Calculate Bollinger Bands.
    Args:
        values (list): List of numerical values (e.g., closing prices).
        period (int): The lookback period for SMA and standard deviation.
        num_std_dev (int): Number of standard deviations for the bands.
    Returns:
        tuple: Upper band, lower band.
    """
    values = np.array(values, dtype=float)
    sma = calc_sma(values, period)
    rolling_std = np.sqrt(np.convolve((values - np.array(sma, dtype=float))**2, np.ones(period)/period, mode='valid'))
    upper_band = sma + num_std_dev * rolling_std
    lower_band = sma - num_std_dev * rolling_std

    return ([None] * (period - 1) + upper_band.tolist(),
            [None] * (period - 1) + lower_band.tolist())

# Average True Range (ATR)
def calc_atr(high, low, close, period=14):
    """
    Calculate the Average True Range (ATR).
    Args:
        high (list): List of high prices.
        low (list): List of low prices.
        close (list): List of closing prices.
        period (int): The lookback period for ATR calculation.
    Returns:
        list: ATR values with None for periods with insufficient data.
    """
    high, low, close = map(np.array, (high, low, close), [float] * 3)
    tr = np.maximum.reduce([high - low, abs(high - close[:-1]), abs(low - close[:-1])])
    atr = np.convolve(tr, np.ones(period)/period, mode='valid')
    return [None] * (period - 1) + atr.tolist()

# Volume Weighted Average Price (VWAP)
def calc_vwap(high, low, close, volume):
    """
    Calculate the Volume Weighted Average Price (VWAP).
    Args:
        high (list): List of high prices.
        low (list): List of low prices.
        close (list): List of closing prices.
        volume (list): List of volumes.
    Returns:
        list: VWAP values.
    """
    typical_price = (np.array(high) + np.array(low) + np.array(close)) / 3
    tp_vol = typical_price * np.array(volume)
    cumsum_tp_vol = np.cumsum(tp_vol)
    cumsum_vol = np.cumsum(volume)
    vwap = cumsum_tp_vol / cumsum_vol
    return vwap.tolist()

# Stochastic Oscillator
def calc_stochastic(high, low, close, period=14):
    """
    Calculate the Stochastic Oscillator.
    Args:
        high (list): List of high prices.
        low (list): List of low prices.
        close (list): List of closing prices.
        period (int): The lookback period.
    Returns:
        tuple: %K and %D values.
    """
    high, low, close = map(np.array, (high, low, close), [float] * 3)
    highest_high = np.convolve(high, np.ones(period), mode='valid')
    lowest_low = np.convolve(low, np.ones(period), mode='valid')

    k = (close[period - 1:] - lowest_low) / (highest_high - lowest_low) * 100
    d = np.convolve(k, np.ones(3)/3, mode='valid')

    return ([None] * (period - 1) + k.tolist(),
            [None] * (period - 1 + 2) + d.tolist())

# Williams %R
def calc_williams_r(high, low, close, period=14):
    """
    Calculate Williams %R.
    Args:
        high (list): List of high prices.
        low (list): List of low prices.
        close (list): List of closing prices.
        period (int): The lookback period.
    Returns:
        list: Williams %R values.
    """
    high, low, close = map(np.array, (high, low, close), [float] * 3)
    highest_high = np.convolve(high, np.ones(period), mode='valid')
    lowest_low = np.convolve(low, np.ones(period), mode='valid')

    williams_r = (highest_high - close[period - 1:]) / (highest_high - lowest_low) * -100
    return [None] * (period - 1) + williams_r.tolist()
