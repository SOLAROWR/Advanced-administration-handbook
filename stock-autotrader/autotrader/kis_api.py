"""한국투자증권 KIS Open API 클라이언트 (REST).

공식 문서: https://apiportal.koreainvestment.com
※ 증권사가 TR ID 등을 바꾸는 경우가 있으니, 오류가 나면 위 문서에서 최신 값을 확인하세요.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

URLS = {
    "real": "https://openapi.koreainvestment.com:9443",
    "paper": "https://openapivts.koreainvestment.com:29443",
}

# 거래 ID (실전/모의가 다름)
TR_IDS = {
    "buy": {"real": "TTTC0012U", "paper": "VTTC0012U"},
    "sell": {"real": "TTTC0011U", "paper": "VTTC0011U"},
    "balance": {"real": "TTTC8434R", "paper": "VTTC8434R"},
    "price": {"real": "FHKST01010100", "paper": "FHKST01010100"},
    "daily": {"real": "FHKST03010100", "paper": "FHKST03010100"},
}


class KISError(Exception):
    pass


class KISClient:
    def __init__(self, app_key, app_secret, account_no, mode="paper",
                 token_path="state/token.json", session=None, min_interval=None):
        if mode not in URLS:
            raise ValueError("mode 는 paper 또는 real")
        acct = account_no.replace("-", "")
        if len(acct) != 10 or not acct.isdigit():
            raise ValueError("계좌번호는 '12345678-01' 형식(숫자 10자리)이어야 합니다.")
        self.app_key = app_key
        self.app_secret = app_secret
        self.cano, self.acnt_prdt_cd = acct[:8], acct[8:]
        self.mode = mode
        self.base_url = URLS[mode]
        self.token_path = Path(token_path)
        self.session = session or requests.Session()
        # 모의투자는 초당 호출 제한이 더 엄격하다
        self.min_interval = min_interval if min_interval is not None else (0.55 if mode == "paper" else 0.06)
        self._last_call = 0.0
        self._token = None
        self._token_expires = None

    # ---------------- 토큰 ----------------
    def _load_cached_token(self):
        if not self.token_path.exists():
            return
        try:
            data = json.loads(self.token_path.read_text(encoding="utf-8"))
            if data.get("mode") != self.mode or data.get("app_key") != self.app_key[:6]:
                return
            self._token = data["access_token"]
            self._token_expires = datetime.fromisoformat(data["expires_at"])
        except (ValueError, KeyError):
            pass

    def _token_valid(self):
        return self._token and self._token_expires and datetime.now() < self._token_expires - timedelta(hours=1)

    def get_token(self, force=False):
        """접근 토큰. 24시간 유효하고 자주 재발급하면 제한이 걸리므로 파일에 저장해서 재사용한다."""
        if not force:
            if not self._token_valid():
                self._load_cached_token()
            if self._token_valid():
                return self._token
        resp = self.session.post(
            f"{self.base_url}/oauth2/tokenP",
            json={"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if "access_token" not in data:
            raise KISError(f"토큰 발급 실패: {data}")
        self._token = data["access_token"]
        self._token_expires = datetime.now() + timedelta(seconds=int(data.get("expires_in", 86400)))
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps({
            "mode": self.mode,
            "app_key": self.app_key[:6],
            "access_token": self._token,
            "expires_at": self._token_expires.isoformat(),
        }), encoding="utf-8")
        log.info("새 접근 토큰 발급 완료")
        return self._token

    # ---------------- 공통 요청 ----------------
    def _throttle(self):
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _request(self, method, path, tr_key, params=None, body=None, _retry=True):
        self._throttle()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.get_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": TR_IDS[tr_key][self.mode],
            "custtype": "P",
        }
        url = f"{self.base_url}{path}"
        if method == "GET":
            resp = self.session.get(url, headers=headers, params=params, timeout=10)
        else:
            resp = self.session.post(url, headers=headers, data=json.dumps(body), timeout=10)
        try:
            data = resp.json()
        except ValueError:
            raise KISError(f"응답 해석 실패 (HTTP {resp.status_code})")
        # 토큰 만료 → 한 번만 재발급 후 재시도
        if _retry and (resp.status_code == 401 or data.get("msg_cd") in ("EGW00123", "EGW00121")):
            self.get_token(force=True)
            return self._request(method, path, tr_key, params, body, _retry=False)
        if data.get("rt_cd") != "0":
            raise KISError(f"[{data.get('msg_cd')}] {data.get('msg1')}")
        return data

    # ---------------- 시세 ----------------
    def get_price(self, code):
        data = self._request("GET", "/uapi/domestic-stock/v1/quotations/inquire-price", "price",
                             params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
        return int(data["output"]["stck_prpr"])

    def get_daily_ohlcv(self, code, count=120, end_date=None):
        """일봉 데이터 (수정주가). 한 번에 최대 100개라 여러 번 나눠 받는다."""
        end = end_date or datetime.now()
        rows = {}
        for _ in range(10):
            start = end - timedelta(days=140)
            data = self._request(
                "GET", "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "daily",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": code,
                    "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "0",
                },
            )
            batch = [r for r in data.get("output2", []) if r and r.get("stck_bsop_date")]
            if not batch:
                break
            for r in batch:
                rows[r["stck_bsop_date"]] = r
            if len(rows) >= count:
                break
            oldest = min(r["stck_bsop_date"] for r in batch)
            end = datetime.strptime(oldest, "%Y%m%d") - timedelta(days=1)

        if not rows:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame([{
            "date": pd.Timestamp(datetime.strptime(d, "%Y%m%d")),
            "open": float(r["stck_oprc"]),
            "high": float(r["stck_hgpr"]),
            "low": float(r["stck_lwpr"]),
            "close": float(r["stck_clpr"]),
            "volume": float(r["acml_vol"]),
        } for d, r in rows.items()])
        df = df.sort_values("date").tail(count).reset_index(drop=True)
        return df

    # ---------------- 계좌 ----------------
    def get_balance(self):
        """예수금, 총평가금액, 보유종목 목록."""
        data = self._request("GET", "/uapi/domestic-stock/v1/trading/inquire-balance", "balance", params={
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        })
        holdings = []
        for h in data.get("output1", []):
            qty = int(float(h.get("hldg_qty", 0)))
            if qty <= 0:
                continue
            holdings.append({
                "code": h["pdno"],
                "name": h.get("prdt_name", ""),
                "qty": qty,
                "avg_price": float(h.get("pchs_avg_pric", 0)),
                "price": float(h.get("prpr", 0)),
            })
        summary = (data.get("output2") or [{}])[0]
        return {
            # D+2 예수금(실제 주문 가능한 현금에 가장 가까운 값)
            "cash": float(summary.get("prvs_rcdl_excc_amt") or summary.get("dnca_tot_amt") or 0),
            "total_asset": float(summary.get("tot_evlu_amt") or 0),
            "holdings": holdings,
        }

    # ---------------- 주문 ----------------
    def order(self, side, code, qty, price=0):
        """side: 'buy' | 'sell'. price=0 이면 시장가, 아니면 지정가."""
        if side not in ("buy", "sell"):
            raise ValueError("side 는 buy 또는 sell")
        if qty <= 0:
            raise ValueError("수량은 1 이상")
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": code,
            "ORD_DVSN": "01" if price == 0 else "00",
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": "0" if price == 0 else str(int(price)),
        }
        data = self._request("POST", "/uapi/domestic-stock/v1/trading/order-cash", side, body=body)
        return data.get("output", {})
