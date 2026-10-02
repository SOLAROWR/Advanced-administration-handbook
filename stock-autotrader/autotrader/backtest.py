"""백테스트: 과거 데이터로 전략을 돌려보고 수익률·승률·최대낙폭을 계산한다.

가정
- 신호는 그날 종가 기준으로 계산하고, 종가에 매매한다 (봇이 15:15에 주문하는 것과 비슷).
- 보유 중에는 매일 고가/저가로 손절·익절 가격 도달 여부를 확인한다.
  같은 날 둘 다 닿으면 보수적으로 손절로 처리한다.
- 한 종목에 현금 전부를 투자한다 (단일 종목 테스트).
"""

from dataclasses import dataclass, field

import pandas as pd

from .strategy import BUY, SELL, add_indicators, signal_at


@dataclass
class Trade:
    entry_date: object
    entry_price: float
    exit_date: object = None
    exit_price: float = None
    reason: str = ""
    return_pct: float = None


@dataclass
class BacktestResult:
    initial_cash: float
    final_equity: float
    trades: list = field(default_factory=list)
    equity_curve: pd.Series = None
    buy_hold_pct: float = 0.0

    @property
    def total_return_pct(self):
        return (self.final_equity / self.initial_cash - 1) * 100

    @property
    def closed_trades(self):
        return [t for t in self.trades if t.exit_price is not None]

    @property
    def win_rate(self):
        closed = self.closed_trades
        if not closed:
            return 0.0
        return sum(1 for t in closed if t.return_pct > 0) / len(closed) * 100

    @property
    def max_drawdown_pct(self):
        if self.equity_curve is None or self.equity_curve.empty:
            return 0.0
        peak = self.equity_curve.cummax()
        return float(((self.equity_curve - peak) / peak).min() * 100)

    def summary(self):
        lines = [
            f"초기자금      : {self.initial_cash:,.0f}원",
            f"최종자산      : {self.final_equity:,.0f}원",
            f"총수익률      : {self.total_return_pct:+.2f}%",
            f"단순보유 수익률: {self.buy_hold_pct:+.2f}%  (비교용: 처음에 사서 그냥 들고 있었다면)",
            f"매매 횟수     : {len(self.closed_trades)}회",
            f"승률          : {self.win_rate:.1f}%",
            f"최대낙폭(MDD) : {self.max_drawdown_pct:.2f}%",
        ]
        return "\n".join(lines)


def run_backtest(df, strategy_cfg, risk_cfg, costs, initial_cash=10_000_000):
    df = df.reset_index(drop=True)
    ind = add_indicators(df, strategy_cfg)
    fee = costs.get("fee_pct", 0) / 100
    tax = costs.get("tax_pct", 0) / 100

    cash = float(initial_cash)
    qty = 0
    trade = None
    trades = []
    equity = []

    def sell(i, price, reason):
        nonlocal cash, qty, trade
        cash += qty * price * (1 - fee - tax)
        trade.exit_date = df.loc[i, "date"] if "date" in df else i
        trade.exit_price = price
        trade.reason = reason
        cost_basis = trade.entry_price * (1 + fee)
        trade.return_pct = (price * (1 - fee - tax) / cost_basis - 1) * 100
        qty = 0
        trade = None

    for i in range(len(df)):
        row = df.loc[i]
        if qty > 0:
            stop = trade.entry_price * (1 + risk_cfg["stop_loss_pct"] / 100)
            target = trade.entry_price * (1 + risk_cfg["take_profit_pct"] / 100)
            if row["low"] <= stop:
                sell(i, min(stop, row["open"]), "손절")
            elif row["high"] >= target:
                sell(i, max(target, row["open"]), "익절")

        sig = signal_at(ind, i, strategy_cfg)
        if qty > 0 and sig.action == SELL:
            sell(i, row["close"], sig.reason)
        elif qty == 0 and sig.action == BUY and i < len(df) - 1:
            price = row["close"]
            n = int(cash // (price * (1 + fee)))
            if n > 0:
                qty = n
                cash -= n * price * (1 + fee)
                trade = Trade(entry_date=df.loc[i, "date"] if "date" in df else i, entry_price=price)
                trades.append(trade)

        equity.append(cash + qty * row["close"])

    final = equity[-1] if equity else initial_cash
    bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100 if len(df) else 0.0
    curve = pd.Series(equity, index=df["date"] if "date" in df else None)
    return BacktestResult(initial_cash, final, trades, curve, bh)


def load_csv(path):
    """CSV(date, open, high, low, close, volume) 읽기."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)
