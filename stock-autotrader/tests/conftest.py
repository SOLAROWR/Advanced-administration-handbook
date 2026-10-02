import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STRATEGY = {"short_ma": 5, "long_ma": 20, "rsi_period": 14, "rsi_buy_max": 70,
            "volume_filter": False, "volume_ma": 20}
RISK = {"max_positions": 2, "position_pct": 30, "stop_loss_pct": -5.0, "take_profit_pct": 10.0,
        "max_buys_per_day": 2, "max_order_amount": 1_000_000}
COSTS = {"fee_pct": 0.015, "tax_pct": 0.20}


def make_df(closes, volume=1000):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "date": pd.bdate_range("2025-01-02", periods=len(closes)),
        "open": closes, "high": closes * 1.01, "low": closes * 0.99,
        "close": closes, "volume": np.full(len(closes), volume, dtype=float),
    })


def golden_cross_closes():
    """완만한 파동 데이터에서 첫 골든크로스(RSI 70 미만) 날까지 잘라서 돌려준다."""
    from autotrader.strategy import add_indicators
    t = np.arange(200)
    closes = 100 + 10 * np.sin(t / 8) + 0.05 * t
    ind = add_indicators(make_df(closes), STRATEGY)
    for i in range(STRATEGY["long_ma"] + 1, len(ind)):
        p, c = ind.iloc[i - 1], ind.iloc[i]
        if p["ma_short"] <= p["ma_long"] and c["ma_short"] > c["ma_long"] and c["rsi"] < 70:
            return list(closes[: i + 1])
    raise AssertionError("골든크로스 없음")


@pytest.fixture
def cfg():
    return {"mode": "paper", "dry_run": False,
            "watchlist": [{"code": "005930", "name": "삼성전자"}, {"code": "000660", "name": "SK하이닉스"},
                          {"code": "035420", "name": "NAVER"}],
            "strategy": dict(STRATEGY), "risk": dict(RISK), "costs": dict(COSTS),
            "schedule": {"signal_time": "15:15", "check_interval_min": 5},
            "holidays": ["2026-10-09"]}
