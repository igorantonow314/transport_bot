import pytest
from random import seed
from data import (
    get_route,
    get_stop,
    get_random_stop_id,
    geo_dist,
    get_nearest_stops,
    get_stops_by_route,
)


def test_get_route():
    route = get_route(1128)
    assert route.route_short_name == '100'
    assert route.transport_type == 'tram'
    assert route.route_long_name == "Ж.-д. станция Ручьи - Придорожная аллея"
    with pytest.raises(ValueError):
        get_route(12345)


def test_get_stop():
    # TODO: different test cases
    stop = get_stop(2080)
    assert stop.stop_name == 'СТ. МЕТРО "МОСКОВСКАЯ"'
    assert stop.transport_type == 'bus'
    assert stop.stop_lat == 59.850751
    assert stop.stop_lon == 30.322769
    with pytest.raises(ValueError):
        get_stop(12345)


def test_get_random_stop_id():
    i = get_random_stop_id()
    assert i
    assert get_stop(i) is not None


@pytest.mark.xfail
def test_geo_dist():
    london_coord = (51.5085300, -0.1257400)
    paris_coord = (48.8534100, 2.3488000)
    dist = geo_dist(*london_coord, *paris_coord)
    assert abs(dist - 342760) < 1000


def check_one_stop(stop_id):
    s = get_stop(stop_id)
    N = 50
    stops = get_nearest_stops(s.stop_lat, s.stop_lon, N)
    last_dist = -1
    for i in stops:
        new_dist = geo_dist(get_stop(i).stop_lat, get_stop(i).stop_lon,
                            s.stop_lat, s.stop_lon)
        assert new_dist >= last_dist*0.99
        last_dist = new_dist


def test_nearest_stops():
    seed(94838208492)
    for i in range(10):
        check_one_stop(get_random_stop_id())


@pytest.mark.skip
def test_get_nearest_stops_full():
    seed(22800210614279115)
    for i in range(100):
        check_one_stop(get_random_stop_id())


def test_get_stops_by_route():
    # Checked by hand
    # This is bus №6
    a = get_stops_by_route(306, 0)
    ans = [22165, 2246, 2424, 2096, 20878, 2278, 1672, 4489, 4497,
           2514, 1294, 1287, 1285, 3248, 1290, 4698, 4498, 1795, 24756,
           3716, 2205, 1343, 2981, 22353, 2840, 2114, 1713, 22150]
    assert a == ans
    a = get_stops_by_route(306, 1)
    ans = [22312, 2909, 3303, 4515, 1632, 17067, 1792, 22153, 4517,
           1676, 4518, 3610, 2595, 2776, 2059, 4519, 22155, 2501, 2508,
           4522, 3244, 3638, 2662, 2875, 3465, 3285, 3605, 24237, 22165]
    assert a == ans
    assert get_stop(a[0]).stop_name == 'СТ.М. "НАРВСКАЯ"'
    assert get_stop(a[1]).stop_name == 'НАРВСКИЙ ПР.'
    assert get_stop(a[3]).stop_name == 'НАБ. ОБВОДНОГО КАНАЛА'
    assert get_stop(a[-1]).stop_name == 'А.С. "НАЛИЧНАЯ УЛ."'
    assert get_stop(a[-2]).stop_name == 'НАЛИЧНАЯ УЛ., УГ. УРАЛЬСКОЙ УЛ. '
    assert get_stop(a[-7]).stop_name == 'ГАВАНСКАЯ УЛ. УГ. МАЛОГО ПР.'


def test_get_stops_by_route_errors():
    with pytest.raises(ValueError):
        get_stops_by_route(312, 0)
