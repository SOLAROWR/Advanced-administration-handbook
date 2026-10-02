"""매매 신호 생성: 이동평균 골든/데드크로스 + RSI + 거래량 필터."""

from dataclasses import dataclass

import pandas as pd

from .indicators import rsi, sma

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"


@dataclass
class Signal:
    action: str
    reason: str


def add_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """df(columns: open, high, low, close, volume)에 지표 컬럼을 추가한 복사본을 돌려준다."""
    out = df.copy()
    out["ma_short"] = sma(out["close"], cfg["short_ma"])
    out["ma_long"] = sma(out["close"], cfg["long_ma"])
    out["rsi"] = rsi(out["close"], cfg["rsi_period"])
    out["vol_ma"] = sma(out["volume"], cfg.get("volume_ma", 20))
    return out


def signal_at(ind: pd.DataFrame, i: int, cfg: dict) -> Signal:
    """지표가 붙은 데이터의 i번째 날(종가 기준) 신호."""
    if i < 1:
        return Signal(HOLD, "데이터 부족")
    prev, cur = ind.iloc[i - 1], ind.iloc[i]
    needed = ("ma_short", "ma_long", "rsi")
    if any(pd.isna(prev[c]) or pd.isna(cur[c]) for c in needed):
        return Signal(HOLD, "데이터 부족")

    golden = prev["ma_short"] <= prev["ma_long"] and cur["ma_short"] > cur["ma_long"]
    dead = prev["ma_short"] >= prev["ma_long"] and cur["ma_short"] < cur["ma_long"]

    if dead:
        return Signal(SELL, f"데드크로스 (MA{cfg['short_ma']} < MA{cfg['long_ma']})")
    if golden:
        if cur["rsi"] >= cfg["rsi_buy_max"]:
            return Signal(HOLD, f"골든크로스지만 RSI {cur['rsi']:.0f} 과열")
        if cfg.get("volume_filter", True):
            if pd.isna(cur["vol_ma"]) or cur["volume"] <= cur["vol_ma"]:
                return Signal(HOLD, "골든크로스지만 거래량 부족")
        return Signal(BUY, f"골든크로스 (RSI {cur['rsi']:.0f})")
    return Signal(HOLD, "신호 없음")


def generate_signal(df: pd.DataFrame, cfg: dict) -> Signal:
    """가장 최근 날짜의 신호."""
    if len(df) < cfg["long_ma"] + 1:
        return Signal(HOLD, "데이터 부족")
    ind = add_indicators(df, cfg)
    return signal_at(ind, len(ind) - 1, cfg)
