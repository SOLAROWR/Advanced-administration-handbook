"""자동매매 봇 본체.

하루 흐름
  09:00~15:30  check_interval_min 마다 보유종목 손절/익절 확인
  signal_time  (기본 15:15) 하루 한 번 매수/매도 신호 계산 후 주문
그 외 시간·주말·휴장일에는 아무것도 하지 않는다.
"""

import csv
import json
import logging
import time
from datetime import datetime, time as dtime
from pathlib import Path

from .risk import calc_buy_qty, check_exit, pnl_pct
from .strategy import BUY, SELL, generate_signal

log = logging.getLogger(__name__)

MARKET_OPEN = dtime(9, 0)
MARKET_CLOSE = dtime(15, 30)


class TradingBot:
    def __init__(self, cfg, client, notifier, state_dir="state", log_dir="logs", clock=datetime.now):
        self.cfg = cfg
        self.client = client
        self.notifier = notifier
        self.clock = clock
        self.state_path = Path(state_dir) / "bot_state.json"
        self.journal_path = Path(log_dir) / "trades.csv"
        self.watch = {w["code"]: w.get("name", w["code"]) for w in cfg["watchlist"]}
        self.state = self._load_state()
        self._last_check = None

    # ---------------- 상태 저장 ----------------
    def _load_state(self):
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except ValueError:
                pass
        return {"last_signal_date": None, "day": None, "buys_today": 0, "sold_today": []}

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")

    def _roll_day(self, today):
        if self.state.get("day") != today:
            self.state.update(day=today, buys_today=0, sold_today=[])
            self._save_state()

    def _journal(self, now, side, code, qty, price, reason):
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.journal_path.exists()
        with self.journal_path.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["시각", "모드", "실제주문", "구분", "종목코드", "종목명", "수량", "가격(참고)", "사유"])
            w.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), self.cfg["mode"], not self.cfg["dry_run"],
                        "매수" if side == "buy" else "매도", code, self.watch.get(code, ""), qty, price, reason])

    # ---------------- 시간 판단 ----------------
    def is_trading_day(self, now):
        return now.weekday() < 5 and now.strftime("%Y-%m-%d") not in self.cfg["holidays"]

    def is_market_open(self, now):
        return self.is_trading_day(now) and MARKET_OPEN <= now.time() < MARKET_CLOSE

    def _signal_time(self):
        h, m = map(int, self.cfg["schedule"]["signal_time"].split(":"))
        return dtime(h, m)

    # ---------------- 주문 ----------------
    def _order(self, now, side, code, qty, price, reason):
        name = self.watch.get(code, code)
        tag = "[모의주문X·기록만]" if self.cfg["dry_run"] else f"[{'모의투자' if self.cfg['mode'] == 'paper' else '실전'}]"
        label = "매수" if side == "buy" else "매도"
        try:
            if not self.cfg["dry_run"]:
                self.client.order(side, code, qty)  # 시장가
        except Exception as e:  # 주문 실패해도 봇은 계속 돈다
            self.notifier.send(f"⚠️ {label} 실패 {name}({code}) {qty}주: {e}")
            return False
        self._journal(now, side, code, qty, price, reason)
        self.notifier.send(f"{tag} {label} {name}({code}) {qty}주 @약 {price:,.0f}원 — {reason}")
        return True

    # ---------------- 핵심 로직 ----------------
    def check_exits(self, now):
        """보유 중인 감시종목의 손절/익절 확인."""
        bal = self.client.get_balance()
        for h in bal["holdings"]:
            if h["code"] not in self.watch:
                continue  # 직접 산 종목은 건드리지 않음
            reason = check_exit(h["avg_price"], h["price"], self.cfg["risk"])
            if reason and self._order(now, "sell", h["code"], h["qty"], h["price"], reason):
                self.state["sold_today"].append(h["code"])
        self._save_state()

    def run_signals(self, now):
        """하루 한 번: 데드크로스 매도 → 골든크로스 매수."""
        bal = self.client.get_balance()
        held = {h["code"]: h for h in bal["holdings"] if h["code"] in self.watch}
        risk = self.cfg["risk"]
        cash = bal["cash"]
        report = []

        for code, name in self.watch.items():
            try:
                df = self.client.get_daily_ohlcv(code, count=max(120, self.cfg["strategy"]["long_ma"] * 3))
                sig = generate_signal(df, self.cfg["strategy"])
            except Exception as e:
                self.notifier.send(f"⚠️ {name}({code}) 데이터 조회 실패: {e}")
                continue
            report.append(f"{name}: {sig.action} ({sig.reason})")

            if code in held and sig.action == SELL:
                h = held[code]
                if self._order(now, "sell", code, h["qty"], h["price"], sig.reason):
                    cash += h["qty"] * h["price"]
                    self.state["sold_today"].append(code)
                    del held[code]

            elif code not in held and sig.action == BUY:
                if code in self.state["sold_today"]:
                    continue
                if len(held) >= risk["max_positions"]:
                    report.append(f"  → 최대 보유종목 수({risk['max_positions']}) 도달, 매수 건너뜀")
                    continue
                if self.state["buys_today"] >= risk["max_buys_per_day"]:
                    report.append("  → 오늘 최대 매수 횟수 도달, 매수 건너뜀")
                    continue
                price = float(df["close"].iloc[-1])
                qty = calc_buy_qty(price, cash, bal["total_asset"] or cash, risk)
                if qty <= 0:
                    report.append("  → 현금 부족, 매수 건너뜀")
                    continue
                if self._order(now, "buy", code, qty, price, sig.reason):
                    cash -= qty * price
                    held[code] = {"code": code, "qty": qty, "avg_price": price, "price": price}
                    self.state["buys_today"] += 1

        self.state["last_signal_date"] = now.strftime("%Y-%m-%d")
        self._save_state()
        self.notifier.send("📊 오늘의 신호\n" + "\n".join(report))

    def run_once(self, now=None):
        now = now or self.clock()
        if not self.is_market_open(now):
            return "closed"
        today = now.strftime("%Y-%m-%d")
        self._roll_day(today)

        interval = self.cfg["schedule"]["check_interval_min"] * 60
        if self._last_check is None or (now - self._last_check).total_seconds() >= interval:
            self.check_exits(now)
            self._last_check = now

        if now.time() >= self._signal_time() and self.state.get("last_signal_date") != today:
            self.run_signals(now)
            return "signals"
        return "checked"

    def status_text(self):
        bal = self.client.get_balance()
        lines = [f"현금 {bal['cash']:,.0f}원 / 총자산 {bal['total_asset']:,.0f}원"]
        for h in bal["holdings"]:
            mark = "🤖" if h["code"] in self.watch else "👤"
            lines.append(f"{mark} {h['name']}({h['code']}) {h['qty']}주 "
                         f"평단 {h['avg_price']:,.0f} 현재 {h['price']:,.0f} ({pnl_pct(h['avg_price'], h['price']):+.2f}%)")
        return "\n".join(lines)

    def run_forever(self, poll_seconds=30):
        mode = "모의투자" if self.cfg["mode"] == "paper" else "실전"
        dry = " (주문 안 보내고 기록만)" if self.cfg["dry_run"] else ""
        self.notifier.send(f"🚀 자동매매 시작: {mode}{dry}, 감시종목 {len(self.watch)}개")
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log.exception("오류")
                self.notifier.send(f"⚠️ 오류 발생 (1분 뒤 재시도): {e}")
                time.sleep(60)
            time.sleep(poll_seconds)
