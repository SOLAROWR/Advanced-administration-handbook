"""pykrx(국내)와 yfinance(해외·국내)로 주식 가격을 가져오는 예제.

사용법:
    pip install pykrx yfinance
    python get_stock_prices.py 005930 AAPL
    python get_stock_prices.py 005930 --days 30

종목 코드가 숫자 6자리이면 pykrx, 그 밖에는 yfinance로 조회한다.
참고: 최신 pykrx는 KRX 로그인(환경 변수 KRX_ID, KRX_PW)이 필요할 수 있다.
"""
import argparse
from datetime import datetime, timedelta

import yfinance as yf
from pykrx import stock


def krx_prices(ticker: str, days: int):
    end = datetime.today()
    start = end - timedelta(days=days)
    return stock.get_market_ohlcv(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker)


def yf_prices(ticker: str, days: int):
    return yf.Ticker(ticker).history(period=f"{days}d")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tickers", nargs="+")
    p.add_argument("--days", type=int, default=10)
    a = p.parse_args()
    for t in a.tickers:
        print(f"\n=== {t} ===")
        df = krx_prices(t, a.days) if t.isdigit() and len(t) == 6 else yf_prices(t, a.days)
        print(df.tail(10))


if __name__ == "__main__":
    main()
