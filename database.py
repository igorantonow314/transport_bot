import pandas as pd
import math
from random import choice
import zipfile
import requests
import os

from rtree import index as rtree_index


def update_feed():
    URL = 'http://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs/feed.zip'
    with open('feed.zip', 'wb') as f:
        r = requests.get(URL)
        f.write(r.content)
        f.close()
    with zipfile.ZipFile('feed.zip') as z:
        z.extractall('feed')
    os.remove('feed.zip')


def get_route(route_id: int):
    r = _route_df[_route_df.route_id == route_id]
    if len(r) == 0:
        return None
    return r.iloc[0]


def get_random_stop_id():
    return choice(_stop_df.stop_id)


def get_stop(stop_id: int):
    r = _stop_df[_stop_df.stop_id == stop_id]
    if len(r) == 0:
        return None
    return r.iloc[0]


def geo_dist(la1, lo1, la2, lo2):
    R= 6371000  # meters
    dLat = math.radians(la2-la1)
    dLon = math.radians(lo2-lo1)
    lat1 = math.radians(la1)
    lat2 = math.radians(la2)

    # half of direct distance (through the Earth)
    a= math.sin(dLat/2)**2 + math.sin(dLon/2)**2 * math.cos(lat1) * math.cos(lat2)
    # the arc length of the unit circle
    c= 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c;
    return d


def get_nearest_stops(lat, lon, n=5):
    '''
    Get the n stops closest to the given coordinates.

    Function uses approximate distance estimation.
    Exact distance:
    2*R * sin(dLat/2)^2 + sin(dLon/2)^2 * cos(lat1)*cos(lat2)
    Approximate distance:
    2*R * (dLat/2)^2 + (dLon/2)^2 * cos(center_lat)^2 ==
    == 1/2 * dLat^2 + (dLon * cos(center_lat))^2
    Error is about cos(max_lat)/cos(min_lat)
    '''
    l = list(_stop_rtree_idx.nearest((lat, 
                                      lon * _koeff), 
                                     num_results=n))
    return l



if not (os.path.exists('feed/routes.txt')
        and os.path.exists('feed/stops.txt')):
    print('downloading files...')
    update_feed()
_route_df = pd.read_csv('feed/routes.txt')
_stop_df = pd.read_csv('feed/stops.txt')

_center_lat = (_stop_df.stop_lat.max() + _stop_df.stop_lat.min()) / 2
# approx. distance = sqrt(dLat^2 + (dLon*cos(lat))^2)
# _koeff = cos(lat)
_koeff = math.cos(math.radians(_center_lat))
_stop_rtree_idx = rtree_index.Index()
for i in _stop_df[['stop_id', 'stop_lat', 'stop_lon']].itertuples():
    _stop_rtree_idx.add(i.stop_id, 
                        (i.stop_lat, 
                         i.stop_lon * _koeff))
