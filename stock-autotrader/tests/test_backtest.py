import numpy as np

from autotrader.backtest import run_backtest
from conftest import COSTS, RISK, STRATEGY, make_df


def test_backtest_runs_on_random_walk():
    rng = np.random.default_rng(0)
    closes = 10000 * np.cumprod(1 + rng.normal(0, 0.02, 400))
    res = run_backtest(make_df(closes), STRATEGY, RISK, COSTS)
    assert len(res.closed_trades) > 0
    assert 0 <= res.win_rate <= 100
    assert res.max_drawdown_pct <= 0
    assert res.final_equity > 0
    assert "총수익률" in res.summary()


def test_backtest_stop_loss_hit():
    # 하락 후 반등(골든크로스 매수) → 이후 급락하면 손절
    from conftest import golden_cross_closes
    closes = golden_cross_closes()
    entry = closes[-1]
    closes += [entry * 0.97, entry * 0.90, entry * 0.85]
    res = run_backtest(make_df(closes), STRATEGY, RISK, COSTS)
    assert res.closed_trades and res.closed_trades[0].reason == "손절"
    assert res.closed_trades[0].return_pct < -5  # 수수료·세금 포함


def test_no_trades_flat():
    res = run_backtest(make_df([100] * 100), STRATEGY, RISK, COSTS, initial_cash=1_000_000)
    assert res.trades == [] and res.final_equity == 1_000_000
