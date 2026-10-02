from datetime import datetime

from autotrader.bot import TradingBot
from conftest import golden_cross_closes, make_df


class FakeClient:
    def __init__(self, holdings=None, cash=10_000_000, data=None):
        self.holdings = holdings or []
        self.cash = cash
        self.data = data or {}
        self.orders = []

    def get_balance(self):
        return {"cash": self.cash, "total_asset": 10_000_000, "holdings": list(self.holdings)}

    def get_daily_ohlcv(self, code, count=120):
        return self.data.get(code, make_df([100] * 60))

    def order(self, side, code, qty, price=0):
        self.orders.append((side, code, qty))


class FakeNotifier:
    def __init__(self):
        self.msgs = []

    def send(self, m):
        self.msgs.append(m)


def make_bot(cfg, client, tmp_path):
    return TradingBot(cfg, client, FakeNotifier(), state_dir=tmp_path / "s", log_dir=tmp_path / "l")


def test_market_hours(cfg, tmp_path):
    bot = make_bot(cfg, FakeClient(), tmp_path)
    assert bot.is_market_open(datetime(2026, 10, 2, 10, 0))      # 금요일
    assert not bot.is_market_open(datetime(2026, 10, 2, 8, 59))
    assert not bot.is_market_open(datetime(2026, 10, 2, 15, 30))
    assert not bot.is_market_open(datetime(2026, 10, 3, 10, 0))  # 토요일
    assert not bot.is_market_open(datetime(2026, 10, 9, 10, 0))  # 휴장일
    assert bot.run_once(datetime(2026, 10, 3, 10, 0)) == "closed"


def test_stop_loss_only_watchlist(cfg, tmp_path):
    holdings = [
        {"code": "005930", "name": "삼성전자", "qty": 10, "avg_price": 100000, "price": 94000},
        {"code": "999999", "name": "내가산종목", "qty": 5, "avg_price": 100000, "price": 50000},
    ]
    client = FakeClient(holdings)
    bot = make_bot(cfg, client, tmp_path)
    bot.run_once(datetime(2026, 10, 2, 10, 0))
    assert client.orders == [("sell", "005930", 10)]  # 직접 산 종목은 안 건드림
    assert (tmp_path / "l" / "trades.csv").exists()


def test_signals_once_per_day_and_limits(cfg, tmp_path):
    gc = make_df(golden_cross_closes())
    data = {"005930": gc, "000660": gc, "035420": gc}
    client = FakeClient(data=data)
    cfg["risk"]["max_buys_per_day"] = 2
    bot = make_bot(cfg, client, tmp_path)

    assert bot.run_once(datetime(2026, 10, 2, 15, 0)) == "checked"
    assert client.orders == []
    assert bot.run_once(datetime(2026, 10, 2, 15, 16)) == "signals"
    buys = [o for o in client.orders if o[0] == "buy"]
    assert len(buys) == 2  # 하루 최대 2회
    assert bot.run_once(datetime(2026, 10, 2, 15, 25)) == "checked"  # 같은 날 재실행 안 함
    assert len([o for o in client.orders if o[0] == "buy"]) == 2


def test_dry_run_sends_no_orders(cfg, tmp_path):
    cfg["dry_run"] = True
    gc = make_df(golden_cross_closes())
    client = FakeClient(data={"005930": gc})
    bot = make_bot(cfg, client, tmp_path)
    bot.run_once(datetime(2026, 10, 2, 15, 20))
    assert client.orders == []
    assert any("기록만" in m for m in bot.notifier.msgs)


def test_dead_cross_sells_holding(cfg, tmp_path):
    dc = make_df([200 - c for c in golden_cross_closes()])
    holdings = [{"code": "000660", "name": "SK하이닉스", "qty": 3, "avg_price": 100, "price": 101}]
    client = FakeClient(holdings, data={"000660": dc})
    bot = make_bot(cfg, client, tmp_path)
    bot.run_once(datetime(2026, 10, 2, 15, 20))
    assert ("sell", "000660", 3) in client.orders


def test_no_rebuy_after_sold_today(cfg, tmp_path):
    gc = make_df(golden_cross_closes())
    holdings = [{"code": "005930", "name": "삼성전자", "qty": 10, "avg_price": 100000, "price": 80000}]
    client = FakeClient(holdings, data={"005930": gc})
    bot = make_bot(cfg, client, tmp_path)
    bot.run_once(datetime(2026, 10, 2, 15, 20))  # 손절 후 같은 날 골든크로스
    client.holdings = []
    assert client.orders == [("sell", "005930", 10)]
