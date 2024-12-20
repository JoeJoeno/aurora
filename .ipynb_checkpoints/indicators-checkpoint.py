import numpy as np

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

def calc_macd(values, fast_period=12, slow_period=26, signal_period=9):
    # Calculate MACD
    ema_fast = calc_ema(values, fast_period)
    ema_slow = calc_ema(values, slow_period)
    macd = [f - s if f is not None and s is not None else None for f, s in zip(ema_fast, ema_slow)]
    signal = calc_sma([m for m in macd if m is not None], signal_period)
    # Align signal with macd
    signal_full = [None]*(len(macd)-len(signal)) + signal
    return macd, signal_full

def calc_stochastic(values, period=14, smooth_k=3, smooth_d=3):
    # Calculate Stochastic Oscillator
    if len(values) < period:
        return [None]*len(values), [None]*len(values)
    stochastic_k = []
    stochastic_d = []
    for i in range(len(values)):
        if i < period-1:
            stochastic_k.append(None)
            stochastic_d.append(None)
        else:
            window = values[i-period+1:i+1]
            min_val = min(window)
            max_val = max(window)
            current = values[i]
            if max_val - min_val == 0:
                k = 0
            else:
                k = ((current - min_val) / (max_val - min_val)) * 100
            stochastic_k.append(k)
    # Smooth %K to get %D
    for i in range(len(stochastic_k)):
        if stochastic_k[i] is None:
            stochastic_d.append(None)
        else:
            if i < smooth_k -1:
                stochastic_d.append(None)
            else:
                window = [k for k in stochastic_k[i-smooth_k+1:i+1] if k is not None]
                if len(window) < smooth_k:
                    stochastic_d.append(None)
                else:
                    stochastic_d.append(np.mean(window))
    return stochastic_k, stochastic_d


def calc_ema(values, period=20):
    # Calculate Exponential Moving Average
    ema = []
    k = 2 / (period + 1)
    ema_current = None
    for i, val in enumerate(values):
        if val is None:
            ema.append(None)
            continue
        if ema_current is None:
            ema_current = val
        else:
            ema_current = val * k + ema_current * (1 - k)
        ema.append(ema_current)
    return ema