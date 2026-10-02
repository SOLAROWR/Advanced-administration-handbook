"""설정 파일(config.yaml)과 비밀정보(.env)를 읽어오는 모듈."""

import os
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


def load_env(path=".env"):
    """간단한 .env 파서. KEY=VALUE 줄을 환경변수로 등록한다 (이미 있는 값은 유지)."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path="config.yaml", env_path=".env"):
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"{path} 파일이 없습니다. config.example.yaml 을 복사해서 {path.name} 으로 만들어주세요."
        )
    load_env(env_path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    cfg.setdefault("mode", "paper")
    cfg.setdefault("dry_run", True)
    if cfg["mode"] not in ("paper", "real"):
        raise ConfigError("mode 는 paper 또는 real 이어야 합니다.")
    for section in ("strategy", "risk", "schedule", "costs"):
        if section not in cfg:
            raise ConfigError(f"config 에 '{section}' 항목이 없습니다.")
    cfg.setdefault("watchlist", [])
    cfg.setdefault("holidays", [])
    # 종목코드가 숫자로 읽혀 앞의 0이 사라지는 실수 방지
    for item in cfg["watchlist"]:
        item["code"] = str(item["code"]).zfill(6)
    cfg["holidays"] = [str(d) for d in cfg["holidays"]]

    cfg["secrets"] = {
        "app_key": os.environ.get("KIS_APP_KEY", ""),
        "app_secret": os.environ.get("KIS_APP_SECRET", ""),
        "account_no": os.environ.get("KIS_ACCOUNT_NO", ""),
        "telegram_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
    }
    return cfg


def check_real_mode_guard(cfg):
    """실전 모드 안전장치: .env 에 I_UNDERSTAND_REAL_MONEY=YES 가 있어야만 실행된다."""
    if cfg["mode"] == "real" and not cfg["dry_run"]:
        if os.environ.get("I_UNDERSTAND_REAL_MONEY", "").upper() != "YES":
            raise ConfigError(
                "실전(real) 모드로 실제 주문을 내려면 .env 에 I_UNDERSTAND_REAL_MONEY=YES 를 적어야 합니다."
            )


def require_secrets(cfg):
    s = cfg["secrets"]
    missing = [k for k in ("app_key", "app_secret", "account_no") if not s[k]]
    if missing:
        raise ConfigError(f".env 에 다음 값이 비어 있습니다: {', '.join(missing)}")
