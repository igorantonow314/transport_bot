import pandas as pd
import math
from random import choice
import zipfile
import requests
import os

from rtree import index as rtree_index


def update_feed_files():
    URL = 'http://transport.orgp.spb.ru/\
Portal/transport/internalapi/gtfs/feed.zip'
    with open('feed.zip', 'wb') as f:
        r = requests.get(URL)
        f.write(r.content)
        f.close()
    with zipfile.ZipFile('feed.zip') as z:
        z.extractall('feed')
    os.remove('feed.zip')


def _load_databases():
    global _route_df
    global _stop_df
    global _stop_times_df
    global _trips_df
    if not (os.path.exists('feed/routes.txt')
            and os.path.exists('feed/stops.txt')
            and os.path.exists('feed/stop_times.txt')
            and os.path.exists('feed/trips.txt')):
        print('downloading files...')
        update_feed_files()
    _route_df = pd.read_csv('feed/routes.txt')
    _stop_df = pd.read_csv('feed/stops.txt')
    _stop_times_df = pd.read_csv('feed/stop_times.txt')
    _trips_df = pd.read_csv('feed/trips.txt')


def _preprocess_stops():
    global _koeff
    global _stop_rtree_idx
    _center_lat = (_stop_df.stop_lat.max() + _stop_df.stop_lat.min()) / 2
    # approx. distance = sqrt(dLat^2 + (dLon*cos(lat))^2)
    # _koeff = cos(lat)
    _koeff = math.cos(math.radians(_center_lat))
    _stop_rtree_idx = rtree_index.Index()
    for i in _stop_df[['stop_id', 'stop_lat', 'stop_lon']].itertuples():
        _stop_rtree_idx.add(i.stop_id,
                            (i.stop_lat,
                             i.stop_lon * _koeff))


def get_route(route_id: int):
    '''
    :return: Series object with properties:
    - route_short_name
    - route_transport_type
    - route_long_name
    '''
    # TODO: return dict or something else
    r = _route_df[_route_df.route_id == route_id]
    if len(r) == 0:
        return None
    return r.iloc[0]


def get_random_stop_id():
    return choice(_stop_df.stop_id)


def get_stop(stop_id: int):
    '''
    :param stop_id: aka stop_code
    :return: Series object with properties:
    - stop_name
    - transport_type
    - stop_lat
    - stop_lon
    '''
    # TODO: return dict or something else
    r = _stop_df[_stop_df.stop_id == stop_id]
    if len(r) == 0:
        return None
    return r.iloc[0]


def geo_dist(la1, lo1, la2, lo2):
    R = 6371000  # meters
    dLat = math.radians(la2-la1)
    dLon = math.radians(lo2-lo1)
    lat1 = math.radians(la1)
    lat2 = math.radians(la2)

    # half of direct distance (through the Earth)
    a = math.sin(dLat/2)**2 + \
        math.sin(dLon/2)**2 * math.cos(lat1) * math.cos(lat2)
    # the arc length of the unit circle
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d


def get_nearest_stops(lat, lon, n=5):
    '''
    Get the n stops closest to the given coordinates.

    Function uses approximate distance estimation.
    Error is about cos(max_lat)/cos(min_lat)
    '''
    # Exact distance:
    # 2*R * sin(dLat/2)^2 + sin(dLon/2)^2 * cos(lat1)*cos(lat2)
    # Approximate distance:
    # 2*R * (dLat/2)^2 + (dLon/2)^2 * cos(center_lat)^2 ==
    # == 1/2 * dLat^2 + (dLon * cos(center_lat))^2
    res = list(_stop_rtree_idx.nearest((lat,
                                        lon * _koeff),
                                       num_results=n))
    return res


def get_stops_by_route(route_id: int, direction_id: int):
    '''
    Returns the list of stops in the correct order.
    :return: list of stop_id
    '''
    if not (_trips_df.route_id == route_id).any():
        raise KeyError(route_id)
    trip_ids = (_trips_df[(_trips_df.route_id == route_id)
                          & (_trips_df.direction_id == direction_id)]
                .trip_id.unique())
    # There are different 'trip' records, but stops sequence doesn't
    # depend on it. It depends only on route_id and direction_id. Difference
    # between 'trip' records is in other fields like arrival_time.
    # I checked it myself.
    # So, let's use trip_ids[0]
    stops = _stop_times_df[_stop_times_df.trip_id == trip_ids[0]]
    ret = stops[['stop_id', 'stop_sequence']].sort_values('stop_sequence')
    return list(ret.stop_id)


def get_direction_by_stop(stop_id: int, route_id: int):
    if stop_id in get_stops_by_route(route_id, 0):
        # also if stop is in both directions
        return 0
    elif stop_id in get_stops_by_route(route_id, 1):
        return 1
    else:
        raise KeyError


_load_databases()
_preprocess_stops()
