"""실행용 공통 함수 (로그 설정, 객체 조립)."""

import logging
from pathlib import Path

from .config import check_real_mode_guard, load_config, require_secrets
from .kis_api import KISClient
from .notifier import Notifier


def setup_logging(log_dir="logs"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(log_dir) / "bot.log", encoding="utf-8"),
        ],
    )


def build(config_path="config.yaml"):
    cfg = load_config(config_path)
    require_secrets(cfg)
    check_real_mode_guard(cfg)
    s = cfg["secrets"]
    client = KISClient(s["app_key"], s["app_secret"], s["account_no"], mode=cfg["mode"])
    notifier = Notifier(s["telegram_token"], s["telegram_chat_id"])
    return cfg, client, notifier
