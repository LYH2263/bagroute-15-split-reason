from app.services.pack_engine import (
    REASON_BOTH,
    REASON_VOLUME,
    REASON_WEIGHT,
    StopItem,
    pack_route,
)


def test_packs_in_route_order_splitting_bags():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.5, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert not result.rejects


def test_reject_oversized_stop():
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2


def test_first_bag_has_no_open_reason():
    # 第一袋不编造开袋原因，即使首站装进去后袋是满的。
    stops = [StopItem(1, 1, 5.0, 5.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.bags) == 1
    assert result.bags[0].open_reason == ""


def test_weight_fill_seed_locks_weight_reason():
    # 纯重量顶满种子：体积余量充足，仅因前袋重量再装不下而开第二袋。
    stops = [
        StopItem(1, 1, 3.0, 1.0, "甲"),
        StopItem(2, 2, 3.0, 1.0, "乙"),
        StopItem(3, 3, 3.0, 1.0, "丙"),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=100.0)
    assert len(result.bags) == 3
    assert [i.stop_id for b in result.bags for i in b.items] == [1, 2, 3]
    assert result.bags[0].open_reason == ""
    assert result.bags[1].open_reason == REASON_WEIGHT
    assert result.bags[1].open_reason == "重量再装不下"
    assert result.bags[2].open_reason == REASON_WEIGHT
    assert not result.rejects


def test_volume_fill_seed_locks_volume_reason():
    # 纯体积顶满种子：重量余量充足，仅因前袋体积再装不下而开第二袋。
    stops = [
        StopItem(1, 1, 1.0, 4.0, "甲"),
        StopItem(2, 2, 1.0, 4.0, "乙"),
        StopItem(3, 3, 1.0, 4.0, "丙"),
    ]
    result = pack_route(stops, max_weight=100.0, max_volume=5.0)
    assert len(result.bags) == 3
    assert [i.stop_id for b in result.bags for i in b.items] == [1, 2, 3]
    assert result.bags[0].open_reason == ""
    assert result.bags[1].open_reason == REASON_VOLUME
    assert result.bags[1].open_reason == "体积再装不下"
    assert result.bags[2].open_reason == REASON_VOLUME
    assert not result.rejects


def test_weight_and_volume_blocked_together_locks_both_reason():
    # 两者同时顶满：下一件同时超出前袋重量与体积余量。
    stops = [
        StopItem(1, 1, 3.0, 3.0, "甲"),
        StopItem(2, 2, 3.0, 3.0, "乙"),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.bags) == 2
    assert result.bags[0].open_reason == ""
    assert result.bags[1].open_reason == REASON_BOTH
    assert result.bags[1].open_reason == "重量、体积均再装不下"


def test_oversized_reject_does_not_write_open_reason():
    # 单站超限仍只走拒收：不因此开袋，也不产生开袋原因。
    stops = [
        StopItem(1, 1, 9.0, 1.0, "超重件"),
        StopItem(2, 2, 1.0, 1.0, "正常件"),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2
    assert result.bags[0].open_reason == ""


def test_reject_between_full_bags_keeps_previous_bag_reason_only():
    # 拒收件夹在两件正常货物之间：第二袋仍因第一袋重量顶满而开，拒收不写原因。
    stops = [
        StopItem(1, 1, 3.0, 1.0, "甲"),
        StopItem(2, 2, 9.0, 1.0, "拒收件"),
        StopItem(3, 3, 3.0, 1.0, "乙"),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=100.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 2
    assert len(result.bags) == 2
    assert [i.stop_id for b in result.bags for i in b.items] == [1, 3]
    assert result.bags[0].open_reason == ""
    assert result.bags[1].open_reason == REASON_WEIGHT
