from app.services.pack_engine import StopItem, pack_route


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
    # 单站超限只走拒收：未因此多开袋，也不写开袋原因。
    assert result.bags[0].open_reason is None


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2


def test_first_bag_has_no_open_reason():
    # 第一袋不编造开袋原因（全部能装下、只开一袋）。
    stops = [StopItem(1, 1, 1.0, 1.0), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 1
    assert result.bags[0].open_reason is None


def test_pure_weight_seed_locks_weight_open_reason():
    # 纯重量顶满种子：体积始终宽松，每次开袋只可能因重量再装不下。
    # 用字面量断言，锁住原因字段的现网文案。
    stops = [
        StopItem(1, 1, 3.0, 1.0),
        StopItem(2, 2, 2.0, 1.0),
        StopItem(3, 3, 3.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=100.0)
    assert len(result.bags) == 3
    assert [[i.stop_id for i in b.items] for b in result.bags] == [[1], [2], [3]]
    assert result.bags[0].open_reason is None
    assert result.bags[1].open_reason == "重量装不下"
    assert result.bags[2].open_reason == "重量装不下"
    assert not result.rejects


def test_pure_volume_seed_locks_volume_open_reason():
    # 纯体积顶满种子：重量始终宽松，每次开袋只可能因体积再装不下。
    stops = [
        StopItem(1, 1, 1.0, 4.0),
        StopItem(2, 2, 1.0, 4.0),
        StopItem(3, 3, 1.0, 4.0),
    ]
    result = pack_route(stops, max_weight=100.0, max_volume=5.0)
    assert len(result.bags) == 3
    assert [[i.stop_id for i in b.items] for b in result.bags] == [[1], [2], [3]]
    assert result.bags[0].open_reason is None
    assert result.bags[1].open_reason == "体积装不下"
    assert result.bags[2].open_reason == "体积装不下"
    assert not result.rejects


def test_both_caps_trigger_combined_open_reason():
    # 当前袋重量、体积同时再装不下 -> 两者同时。
    stops = [StopItem(1, 1, 4.0, 4.0), StopItem(2, 2, 4.0, 4.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.bags) == 2
    assert result.bags[0].open_reason is None
    assert result.bags[1].open_reason == "重量、体积均装不下"
    assert not result.rejects


def test_oversized_stop_does_not_set_open_reason_on_following_bag():
    # 拒收件不占袋；它后面的正常件进第一袋，第一袋仍无开袋原因。
    stops = [
        StopItem(1, 1, 9.0, 9.0, "双超件"),
        StopItem(2, 2, 1.0, 1.0),
        StopItem(3, 3, 5.0, 5.0),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert [i.stop_id for i in result.bags[0].items] == [2]
    assert result.bags[0].open_reason is None
    # 袋 2 由正常顶满触发（1+5>5 双维度），与拒收无关。
    assert result.bags[1].open_reason == "重量、体积均装不下"
