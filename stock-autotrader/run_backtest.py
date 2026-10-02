"""백테스트 (과거 데이터로 전략 성적 확인).

  python run_backtest.py --code 005930 --days 500   # KIS API로 데이터 받아서 테스트
  python run_backtest.py --csv data/samsung.csv     # CSV 파일로 테스트
  python run_backtest.py --all --days 500           # 감시종목 전체 테스트
"""

import argparse
import sys

from autotrader.backtest import load_csv, run_backtest
from autotrader.config import ConfigError, load_config


def main():
    p = argparse.ArgumentParser(description="전략 백테스트")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--csv", help="date,open,high,low,close,volume 컬럼의 CSV 파일")
    p.add_argument("--code", help="종목코드 (KIS API 사용)")
    p.add_argument("--all", action="store_true", help="감시종목 전체")
    p.add_argument("--days", type=int, default=500, help="거래일 수")
    p.add_argument("--cash", type=float, default=10_000_000, help="초기자금(원)")
    p.add_argument("--save", action="store_true", help="받은 데이터를 data/ 폴더에 CSV로 저장")
    args = p.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"설정 오류: {e}")
        sys.exit(1)

    jobs = []
    if args.csv:
        jobs.append((args.csv, load_csv(args.csv)))
    else:
        from autotrader.app import build
        _, client, _ = build(args.config)
        codes = [w["code"] for w in cfg["watchlist"]] if args.all else [args.code]
        if not codes or codes == [None]:
            p.error("--csv, --code, --all 중 하나를 지정하세요")
        for code in codes:
            df = client.get_daily_ohlcv(code, count=args.days)
            if args.save:
                df.to_csv(f"data/{code}.csv", index=False)
            jobs.append((code, df))

    for label, df in jobs:
        res = run_backtest(df, cfg["strategy"], cfg["risk"], cfg["costs"], args.cash)
        start, end = df["date"].iloc[0].date(), df["date"].iloc[-1].date()
        print(f"\n===== {label}  ({start} ~ {end}, {len(df)}일) =====")
        print(res.summary())
        for t in res.closed_trades:
            print(f"  {t.entry_date.date()} {t.entry_price:,.0f} → {t.exit_date.date()} "
                  f"{t.exit_price:,.0f}  {t.return_pct:+.2f}%  ({t.reason})")


if __name__ == "__main__":
    main()
