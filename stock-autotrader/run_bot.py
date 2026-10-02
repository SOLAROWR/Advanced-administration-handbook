"""자동매매 실행.

  python run_bot.py           # 자동매매 시작 (Ctrl+C 로 종료)
  python run_bot.py --status  # 연결 확인 + 계좌 잔고 보기
  python run_bot.py --signals # 지금 바로 감시종목 신호만 보기 (주문 안 함)
"""

import argparse
import sys

from autotrader.app import build, setup_logging
from autotrader.bot import TradingBot
from autotrader.config import ConfigError
from autotrader.strategy import generate_signal


def main():
    p = argparse.ArgumentParser(description="국내주식 자동매매")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--status", action="store_true", help="계좌 잔고 확인")
    p.add_argument("--signals", action="store_true", help="오늘 신호만 확인 (주문 없음)")
    args = p.parse_args()

    setup_logging()
    try:
        cfg, client, notifier = build(args.config)
    except ConfigError as e:
        print(f"설정 오류: {e}")
        sys.exit(1)

    bot = TradingBot(cfg, client, notifier)
    if args.status:
        print(bot.status_text())
        return
    if args.signals:
        for code, name in bot.watch.items():
            df = client.get_daily_ohlcv(code)
            sig = generate_signal(df, cfg["strategy"])
            print(f"{name}({code}) 종가 {df['close'].iloc[-1]:,.0f}원 → {sig.action} ({sig.reason})")
        return
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        notifier.send("🛑 자동매매 종료")


if __name__ == "__main__":
    main()
