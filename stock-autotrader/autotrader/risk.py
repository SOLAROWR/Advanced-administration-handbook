"""위험 관리: 손절/익절 판단과 매수 수량 계산."""


def pnl_pct(avg_price: float, price: float) -> float:
    if avg_price <= 0:
        return 0.0
    return (price - avg_price) / avg_price * 100


def check_exit(avg_price: float, price: float, cfg: dict):
    """손절/익절 조건에 걸리면 사유 문자열, 아니면 None."""
    p = pnl_pct(avg_price, price)
    if p <= cfg["stop_loss_pct"]:
        return f"손절 ({p:+.2f}%)"
    if p >= cfg["take_profit_pct"]:
        return f"익절 ({p:+.2f}%)"
    return None


def calc_buy_qty(price: float, cash: float, total_asset: float, cfg: dict) -> int:
    """살 수 있는 주식 수. 총자산 비중 한도, 1회 주문 한도, 보유 현금 중 가장 작은 금액 기준."""
    if price <= 0:
        return 0
    budget = min(
        total_asset * cfg["position_pct"] / 100,
        cfg.get("max_order_amount", float("inf")),
        cash,
    )
    return max(int(budget // price), 0)
