"""보조지표 계산 (이동평균, RSI)."""

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """단순 이동평균."""
    return series.rolling(window=period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Wilder 방식). 0~100, 70 이상 과열 / 30 이하 침체."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100 - (100 / (1 + rs))
    # 하락이 전혀 없으면 RSI=100
    out = out.where(avg_loss != 0, 100.0)
    return out.where(avg_gain.notna())
