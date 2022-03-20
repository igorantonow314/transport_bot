import pytest
from random import seed
from database import (
    get_route,
    get_stop,
    get_random_stop_id,
    geo_dist,
    get_nearest_stops,
)


def test_get_route():
    route = get_route(1128)
    assert route.route_short_name == '100'
    assert route.transport_type == 'tram'
    assert route.route_long_name == "Ж.-д. станция Ручьи - Придорожная аллея"


def test_get_stop():
    # TODO: different test cases
    stop = get_stop(2080)
    assert stop.stop_name == 'СТ. МЕТРО "МОСКОВСКАЯ"'
    assert stop.transport_type == 'bus'
    assert stop.stop_lat == 59.850751
    assert stop.stop_lon == 30.322769


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
