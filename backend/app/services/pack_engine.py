"""Route-order bag packing with weight + volume caps; reject when exceed."""

from __future__ import annotations

from dataclasses import dataclass, field

# 开袋原因：除首袋外，新袋因前一袋在该约束下再装不下当前件而开。
# 文字直接落库，装袋页与袋明细页共用同一字段，保持两页一致。
REASON_WEIGHT = "重量再装不下"
REASON_VOLUME = "体积再装不下"
REASON_BOTH = "重量、体积均再装不下"


@dataclass(frozen=True)
class StopItem:
    stop_id: int
    seq: int
    weight_kg: float
    volume_l: float
    label: str = ""


@dataclass
class Bag:
    bag_index: int
    items: list[StopItem] = field(default_factory=list)
    weight_kg: float = 0.0
    volume_l: float = 0.0
    # 首袋无开袋原因；其余袋记录前袋装不下当前件的约束原因。
    open_reason: str = ""


@dataclass(frozen=True)
class PackResult:
    bags: list[Bag]
    rejects: list[tuple[StopItem, str]]


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + 1e-9
        and bag.volume_l + item.volume_l <= max_volume + 1e-9
    )


def open_reason_for(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> str:
    """前袋装入当前件时触发超限的约束，即本袋的开袋原因。"""
    weight_blocked = bag.weight_kg + item.weight_kg > max_weight + 1e-9
    volume_blocked = bag.volume_l + item.volume_l > max_volume + 1e-9
    if weight_blocked and volume_blocked:
        return REASON_BOTH
    if weight_blocked:
        return REASON_WEIGHT
    if volume_blocked:
        return REASON_VOLUME
    return ""


def pack_route(
    stops: list[StopItem],
    max_weight: float,
    max_volume: float,
) -> PackResult:
    ordered = sorted(stops, key=lambda s: s.seq)
    bags: list[Bag] = []
    rejects: list[tuple[StopItem, str]] = []
    current: Bag | None = None

    for item in ordered:
        if item.weight_kg > max_weight or item.volume_l > max_volume:
            reason = []
            if item.weight_kg > max_weight:
                reason.append(f"超重 {item.weight_kg}>{max_weight}")
            if item.volume_l > max_volume:
                reason.append(f"超体积 {item.volume_l}>{max_volume}")
            # 单站超限只走拒收：不开新袋，也不写开袋原因。
            rejects.append((item, "；".join(reason)))
            continue

        if current is None or not can_fit(current, item, max_weight, max_volume):
            # 首袋不编造开袋原因；仅在因前袋装不下而开新袋时记录。
            reason = "" if current is None else open_reason_for(current, item, max_weight, max_volume)
            current = Bag(bag_index=len(bags) + 1, open_reason=reason)
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            # should not happen after single-item check, but keep safe
            rejects.append((item, "无法装入新袋"))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l

    return PackResult(bags=bags, rejects=rejects)
