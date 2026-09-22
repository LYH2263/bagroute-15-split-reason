"""Route-order bag packing with weight + volume caps; reject when exceed."""

from __future__ import annotations

from dataclasses import dataclass, field

# 开袋原因：袋 2..N 在“当前袋再装不下”时开启，第一袋不编造原因。
# 同一原因文案由后端单点定义，装袋页与袋明细共用，保证两页文字一致。
OPEN_REASON_WEIGHT = "重量装不下"
OPEN_REASON_VOLUME = "体积装不下"
OPEN_REASON_BOTH = "重量、体积均装不下"


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
    # 第一袋为 None；其余袋记录开启它的原因（当前袋重量/体积再装不下）。
    open_reason: str | None = None


@dataclass(frozen=True)
class PackResult:
    bags: list[Bag]
    rejects: list[tuple[StopItem, str]]


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + 1e-9
        and bag.volume_l + item.volume_l <= max_volume + 1e-9
    )


def _blocked_dimensions(
    bag: Bag, item: StopItem, max_weight: float, max_volume: float
) -> list[str]:
    """当前袋再装该件时装不下的维度。"""
    blocked: list[str] = []
    if bag.weight_kg + item.weight_kg > max_weight + 1e-9:
        blocked.append(OPEN_REASON_WEIGHT)
    if bag.volume_l + item.volume_l > max_volume + 1e-9:
        blocked.append(OPEN_REASON_VOLUME)
    return blocked


def _open_reason_for(blocked: list[str]) -> str:
    if len(blocked) == 2:
        return OPEN_REASON_BOTH
    return blocked[0]


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
            # 单站自身超限：只走拒收，不开新袋，不写开袋原因。
            reason = []
            if item.weight_kg > max_weight:
                reason.append(f"超重 {item.weight_kg}>{max_weight}")
            if item.volume_l > max_volume:
                reason.append(f"超体积 {item.volume_l}>{max_volume}")
            rejects.append((item, "；".join(reason)))
            continue

        if current is None:
            # 第一袋：不编造开袋原因。
            current = Bag(bag_index=len(bags) + 1)
            bags.append(current)
        elif not can_fit(current, item, max_weight, max_volume):
            # 当前袋再装不下 -> 开新袋，原因是装不下的（一个或两个）维度。
            blocked = _blocked_dimensions(current, item, max_weight, max_volume)
            current = Bag(
                bag_index=len(bags) + 1,
                open_reason=_open_reason_for(blocked),
            )
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            # should not happen after single-item check, but keep safe
            rejects.append((item, "无法装入新袋"))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l

    return PackResult(bags=bags, rejects=rejects)
