import numpy as np

from autotrader.indicators import rsi, sma
from autotrader.risk import calc_buy_qty, check_exit
from autotrader.strategy import BUY, HOLD, SELL, generate_signal
from conftest import STRATEGY, golden_cross_closes, make_df


def test_sma():
    s = make_df([1, 2, 3, 4, 5])["close"]
    out = sma(s, 3)
    assert np.isnan(out.iloc[1])
    assert out.iloc[-1] == 4


def test_rsi_bounds():
    up = rsi(make_df(range(1, 40))["close"], 14)
    assert up.iloc[-1] == 100
    down = rsi(make_df(range(40, 1, -1))["close"], 14)
    assert down.iloc[-1] < 1


def test_not_enough_data_is_hold():
    assert generate_signal(make_df([100] * 10), STRATEGY).action == HOLD


def test_golden_cross_buy():
    sig = generate_signal(make_df(golden_cross_closes()), STRATEGY)
    assert sig.action == BUY, sig.reason


def test_golden_cross_blocked_by_rsi():
    cfg = dict(STRATEGY, rsi_buy_max=10)
    sig = generate_signal(make_df(golden_cross_closes()), cfg)
    assert sig.action == HOLD and "RSI" in sig.reason


def test_golden_cross_blocked_by_volume():
    cfg = dict(STRATEGY, volume_filter=True)
    sig = generate_signal(make_df(golden_cross_closes()), cfg)  # 거래량이 평균과 같음
    assert sig.action == HOLD and "거래량" in sig.reason


def test_dead_cross_sell():
    closes = [200 - c for c in golden_cross_closes()]  # 위아래 뒤집기
    assert generate_signal(make_df(closes), STRATEGY).action == SELL


def test_check_exit():
    risk = {"stop_loss_pct": -5, "take_profit_pct": 10}
    assert check_exit(10000, 9500, risk).startswith("손절")
    assert check_exit(10000, 11000, risk).startswith("익절")
    assert check_exit(10000, 10300, risk) is None


def test_calc_buy_qty_limits():
    risk = {"position_pct": 30, "max_order_amount": 1_000_000}
    # 총자산 1천만의 30% = 300만이지만 1회 한도 100만 → 100만/7만 = 14주
    assert calc_buy_qty(70000, 5_000_000, 10_000_000, risk) == 14
    # 현금이 더 적으면 현금 기준
    assert calc_buy_qty(70000, 200_000, 10_000_000, risk) == 2
    assert calc_buy_qty(0, 1e9, 1e9, risk) == 0
