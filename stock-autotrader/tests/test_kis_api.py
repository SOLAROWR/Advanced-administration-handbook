import json

import pytest

from autotrader.kis_api import KISClient, KISError


class Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status

    def json(self):
        return self._d


class FakeSession:
    def __init__(self):
        self.calls = []
        self.daily_pages = []

    def post(self, url, json=None, data=None, headers=None, timeout=None):
        self.calls.append(("POST", url, json or data, headers))
        if url.endswith("/oauth2/tokenP"):
            return Resp({"access_token": "TOKEN", "expires_in": 86400})
        return Resp({"rt_cd": "0", "msg1": "ok", "output": {"ODNO": "1"}})

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        if "itemchartprice" in url:
            page = self.daily_pages.pop(0) if self.daily_pages else []
            return Resp({"rt_cd": "0", "output2": page})
        if "inquire-price" in url:
            return Resp({"rt_cd": "0", "output": {"stck_prpr": "71500"}})
        if "inquire-balance" in url:
            return Resp({"rt_cd": "0", "output1": [
                {"pdno": "005930", "prdt_name": "삼성전자", "hldg_qty": "10", "pchs_avg_pric": "70000.0", "prpr": "71500"},
                {"pdno": "000660", "prdt_name": "x", "hldg_qty": "0", "pchs_avg_pric": "0", "prpr": "0"},
            ], "output2": [{"prvs_rcdl_excc_amt": "5000000", "tot_evlu_amt": "5715000"}]})
        return Resp({"rt_cd": "1", "msg_cd": "X", "msg1": "에러"})


def client(tmp_path, mode="paper"):
    s = FakeSession()
    return KISClient("APPKEY123", "SECRET", "12345678-01", mode=mode,
                     token_path=tmp_path / "t.json", session=s, min_interval=0), s


def test_bad_account(tmp_path):
    with pytest.raises(ValueError):
        KISClient("a", "b", "1234", token_path=tmp_path / "t.json")


def test_token_cached_to_file(tmp_path):
    c, s = client(tmp_path)
    c.get_price("005930")
    c.get_price("005930")
    assert sum(1 for x in s.calls if x[1].endswith("tokenP")) == 1
    c2, s2 = client(tmp_path)  # 새 실행 → 파일에서 재사용
    c2.get_price("005930")
    assert not any(x[1].endswith("tokenP") for x in s2.calls)


def test_paper_vs_real_order(tmp_path):
    c, s = client(tmp_path, "paper")
    c.order("buy", "005930", 3)
    _, url, body, headers = s.calls[-1]
    assert "openapivts" in url and headers["tr_id"] == "VTTC0012U"
    body = json.loads(body)
    assert body["ORD_DVSN"] == "01" and body["ORD_QTY"] == "3" and body["CANO"] == "12345678"

    c, s = client(tmp_path / "r", "real")
    c.order("sell", "005930", 1, price=70000)
    _, url, body, headers = s.calls[-1]
    assert ":9443" in url and headers["tr_id"] == "TTTC0011U"
    assert json.loads(body)["ORD_DVSN"] == "00"


def test_balance(tmp_path):
    c, _ = client(tmp_path)
    b = c.get_balance()
    assert b["cash"] == 5_000_000
    assert len(b["holdings"]) == 1 and b["holdings"][0]["avg_price"] == 70000


def test_daily_paging(tmp_path):
    c, s = client(tmp_path)

    def rows(start_day, n):
        from datetime import date, timedelta
        d0 = date(2026, 1, 1)
        return [{"stck_bsop_date": (d0 + timedelta(days=start_day + i)).strftime("%Y%m%d"),
                 "stck_oprc": "1", "stck_hgpr": "2", "stck_lwpr": "1", "stck_clpr": "1.5", "acml_vol": "10"}
                for i in range(n)]
    s.daily_pages = [rows(100, 100), rows(30, 70)]
    df = c.get_daily_ohlcv("005930", count=150)
    assert len(df) == 150
    assert df["date"].is_monotonic_increasing


def test_api_error(tmp_path):
    c, _ = client(tmp_path)
    with pytest.raises(KISError):
        c._request("GET", "/unknown", "price")
