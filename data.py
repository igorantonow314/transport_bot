import pandas as pd
import math
import json
from random import choice
import zipfile
import requests
import os
from typing import Optional, List, Tuple
import logging

from rtree import index as rtree_index  # type: ignore
from fuzzywuzzy import process
from fuzzywuzzy import fuzz


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_route_df: Optional[pd.DataFrame] = None
_stop_df: Optional[pd.DataFrame] = None
_stop_times_df: Optional[pd.DataFrame] = None
_trips_df: Optional[pd.DataFrame] = None


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
    logger.info('loading databases...')
    global _route_df
    global _stop_df
    global _stop_times_df
    global _trips_df
    if not (os.path.exists('feed/routes.txt')
            and os.path.exists('feed/stops.txt')
            and os.path.exists('feed/stop_times.txt')
            and os.path.exists('feed/trips.txt')):
        logger.warn('downloading files...')
        update_feed_files()
        logger.info('files downloaded')
    _route_df = pd.read_csv('feed/routes.txt')
    _stop_df = pd.read_csv('feed/stops.txt')
    _stop_times_df = pd.read_csv('feed/stop_times.txt')
    _trips_df = pd.read_csv('feed/trips.txt')


def _preprocess_stops():
    logger.info('preprocessing stops...')
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


def get_route(route_id: int) -> pd.Series:
    '''
    :return: Series object with properties:
    - route_short_name
    - route_transport_type
    - route_long_name
    '''
    # TODO: return dict or something else
    assert _route_df is not None
    r = _route_df[_route_df.route_id == route_id]
    if len(r) == 0:
        raise ValueError(f'''Cannot find routes with id {route_id},
            maybe your databases (feed) are outdated?''')
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
    assert _stop_df is not None
    r = _stop_df[_stop_df.stop_id == stop_id]
    if len(r) == 0:
        raise ValueError(f'Cannot find stops with id {stop_id}')
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
    assert _trips_df is not None
    assert _stop_times_df is not None
    if not (_trips_df.route_id == route_id).any():
        raise ValueError(f'Cannot find trips for route_id={route_id}')
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


def get_forecast_by_stop(stopID):
    '''
    Requests arrival time forecast for a particular stop.

    See also forecast_json_to_text() for human-readable result.
    Data from site: transport.orgp.spb.ru
    '''
    assert get_stop(int(stopID)) is not None
    data_url = "https://transport.orgp.spb.ru/\
Portal/transport/internalapi/forecast/bystop?stopID="+str(stopID)
    d = requests.get(data_url)
    if d.status_code != 200:
        raise ValueError
    forecast_json = d.content
    return json.loads(forecast_json)


def search_stop_groups_by_name(query: str, cutoff=0.5) -> List[str]:
    """Searches in stop_names in lowercase, drops duplicates
       :return: List of stop names in lowercase. Each stop name in
       lowercase may correspond to different stop_name
    """
    assert _stop_df is not None
    stop_names = _stop_df.stop_name.str.lower().unique()
    result = process.extractBests(
        query,
        stop_names,
        scorer=fuzz.token_sort_ratio,
        limit=10
    )
    result = [i[0] for i in result if i[1] > cutoff]
    return result


def get_stops_in_group(stop_name: str) -> List[int]:
    """
    :param stop_name: stop name in lowercase
    :return: list of stop_id
    """
    assert _stop_df is not None
    res = _stop_df[_stop_df.stop_name.str.lower() == stop_name].stop_id
    return list(res)


def get_routes_by_stop(stop_id: int) -> List[Tuple[int, int]]:
    """
    :return: list of (route_id, direction_id)
    """
    assert _stop_times_df is not None
    assert _trips_df is not None
    # stop_id -> list(trip_id)
    t_trips = (_stop_times_df[_stop_times_df.stop_id == stop_id]
               .trip_id.unique()
               )
    # list(trip_id) -> DataFrame((route_id, direction_id))
    t = (
           _trips_df[_trips_df.trip_id.isin(t_trips)]
           [['route_id', 'direction_id']]
           .drop_duplicates()
           )
    # DataFrame((route_id, direction_id)) -> list(tuple(route_id, direction))
    ret = [(i[1].route_id, i[1].direction_id) for i in t.iterrows()]
    return ret


_load_databases()
_preprocess_stops()
