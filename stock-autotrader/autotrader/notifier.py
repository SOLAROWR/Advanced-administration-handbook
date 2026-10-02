"""알림: 로그 기록 + (선택) 텔레그램으로 휴대폰 알림."""

import logging

import requests

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, telegram_token="", chat_id="", session=None):
        self.token = telegram_token
        self.chat_id = chat_id
        self.session = session or requests.Session()

    def send(self, message):
        log.info(message)
        if not (self.token and self.chat_id):
            return
        try:
            self.session.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message},
                timeout=5,
            )
        except requests.RequestException as e:
            log.warning("텔레그램 전송 실패: %s", e)
