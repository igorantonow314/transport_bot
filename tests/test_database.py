import pytest
from random import seed
from database import get_nearest_stops, get_random_stop_id, get_stop, geo_dist



def check_one_stop(stop_id):
    s = get_stop(stop_id)
    N = 50
    l = get_nearest_stops(s.stop_lat, s.stop_lon, N)
    last_dist = -1
    for i in l:
        new_dist = geo_dist(get_stop(i).stop_lat, get_stop(i).stop_lon, s.stop_lat, s.stop_lon)
        assert new_dist >= last_dist*0.99
        last_dist = new_dist


def test_get_nearest_stops():
    seed(22800210614279115)
    for i in range(100):
        check_one_stop(get_random_stop_id())
